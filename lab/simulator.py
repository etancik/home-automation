"""Deterministic MQTT devices; temperatures are inputs, not a thermal house model.

Control via compose exec simulator python /lab/simulator.py '{"room":"bedroom","temperature":19}'.
Other controls: window (on/off), mode, target, available (online/offline).
Relay fault: {"relay":"laundry_room_boiler_controller_l2","fail":"on"}.
"""
import json
import sys
import time
import threading
import paho.mqtt.client as mqtt

ROOMS=['bedroom','kids_room','workshop','entrance','downstairs_bathroom','upstairs_bathroom','living_room']
CONTACTS={'bedroom':'bedroom_window','kids_room':'kids_room_window','workshop':'workshop_window','entrance':'entrance_door','kitchen':'kitchen_window','living_room':'living_room_door'}
RELAYS=['laundry_room_boiler_controller_l2','floor_heating_controller_l1','floor_heating_controller_l2']
state={r:{'temperature':21.0,'perceived':21.0,'mode':'heat','target':21.0,'action':'idle','available':'online'} for r in ROOMS}
windows={r:'off' for r in CONTACTS}
relays={r:'off' for r in RELAYS}
faults={}
lock=threading.RLock()
client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='heating-lab-simulator' if len(sys.argv)==1 else '')

def pub(topic,value,retain=True):
    return client.publish(topic,json.dumps(value) if isinstance(value,dict) else str(value),qos=1,retain=retain)

def discovery(domain,eid,**config):
    pub(f'homeassistant/{domain}/heating_lab_{eid}/config',dict(name=eid.replace('_',' ').title(),unique_id='heating_lab_'+eid,default_entity_id=domain+'.'+eid,**config))

def publish_state():
    with lock:
        for room,s in state.items():
            pub(f'lab/{room}/temperature',s['temperature'])
            pub(f'lab/{room}/perceived',s['perceived'])
            pub(f'lab/{room}/mode',s['mode'])
            pub(f'lab/{room}/target',s['target'])
            if s['mode']=='off': s['action']='idle'
            elif s['perceived'] <= s['target']-0.2: s['action']='heating'
            elif s['perceived'] >= s['target']: s['action']='idle'
            pub(f'lab/{room}/action',s['action'])
            pub(f'lab/{room}/available',s['available'])
        for room,value in windows.items(): pub(f'lab/{room}/window',value)
        for relay,value in relays.items(): pub(f'lab/relay/{relay}/state',value)

def connect(c,u,f,reason,properties):
    if reason.is_failure: return
    c.subscribe([('lab/+/temperature/set',1),('lab/+/window/set',1),('lab/relay/+/set',1),('zigbee2mqtt/+/set',1),('lab/control',1)])
    for room in ROOMS:
        availability=dict(availability_topic=f'lab/{room}/available')
        discovery('sensor',f'{room}_temperature_sensor_temperature',state_topic=f'lab/{room}/temperature',unit_of_measurement='°C',device_class='temperature',state_class='measurement',expire_after=60,**availability)
        discovery('number',f'lab_{room}_temperature',state_topic=f'lab/{room}/temperature',command_topic=f'lab/{room}/temperature/set',min=5,max=35,step=0.1,unit_of_measurement='°C')
        if room!='living_room':
            topic='zigbee2mqtt/'+room.replace('_',' ').title()+' Radiator Heat Valve/set'
            discovery('climate',f'{room}_radiator_heat_valve',modes=['off','heat','auto'],min_temp=4,max_temp=35,temp_step=0.5,
                current_temperature_topic=f'lab/{room}/perceived',temperature_state_topic=f'lab/{room}/target',temperature_command_topic=topic,
                temperature_command_template='{"occupied_heating_setpoint": {{ value }}}',mode_state_topic=f'lab/{room}/mode',mode_command_topic=topic,
                mode_command_template='{"system_mode": "{{ value }}"}',action_topic=f'lab/{room}/action',**availability)
    for room,contact in CONTACTS.items():
        discovery('binary_sensor',contact+'_sensor_contact',state_topic=f'lab/{room}/window',payload_on='on',payload_off='off',device_class='opening')
        discovery('switch',f'lab_{room}_window',state_topic=f'lab/{room}/window',command_topic=f'lab/{room}/window/set',payload_on='on',payload_off='off')
    for relay in RELAYS:
        discovery('switch',relay,state_topic=f'lab/relay/{relay}/state',command_topic=f'lab/relay/{relay}/set',payload_on='on',payload_off='off')
    pub('zigbee2mqtt/bridge/state',{'state':'online'})
    publish_state()

def message(c,u,msg):
    text=msg.payload.decode(); parts=msg.topic.split('/')
    with lock:
        if msg.topic=='lab/control':
            control=json.loads(text)
            if 'relay' in control: faults[control['relay']]=control.get('fail','')
            else:
                room=control['room']
                if 'window' in control: windows[room]=control['window']
                if room in state:
                    state[room].update({k:v for k,v in control.items() if k in state[room]})
        elif parts[0]=='zigbee2mqtt':
            room=parts[1].removesuffix(' Radiator Heat Valve').lower().replace(' ','_')
            if room not in state: return
            values=json.loads(text)
            for source,target in [('system_mode','mode'),('occupied_heating_setpoint','target'),('external_temperature_input','perceived')]:
                if source in values: state[room][target]=values[source]
        elif parts[1]=='relay':
            if faults.get(parts[2])!=text: relays[parts[2]]=text
            print('relay command',parts[2],text,'reported',relays[parts[2]],flush=True)
        elif parts[2]=='temperature': state[parts[1]]['temperature']=float(text)
        elif parts[2]=='window': windows[parts[1]]=text
    publish_state()

if len(sys.argv)>1:
    client.connect('mqtt'); client.loop_start()
    client.publish('lab/control',json.dumps(json.loads(sys.argv[1])),qos=1).wait_for_publish()
    client.disconnect(); client.loop_stop()
else:
    client.on_connect=connect; client.on_message=message
    client.connect('mqtt'); client.loop_start()
    while True:
        time.sleep(10)
        publish_state()
