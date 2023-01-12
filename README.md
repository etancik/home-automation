## OS Install

### Ignition file

https://docs.fedoraproject.org/en-US/fedora-coreos/producing-ign/

https://docs.fedoraproject.org/en-US/fedora-coreos/authentication/

https://github.com/coreos/butane/releases

To change regenerate ignition file for the yaml config
```shell
butane --pretty --strict ignite.bu > ignite.ign
```
To serve ignition file
```shell
python3 -m http.server
```

### Base Instalation

https://docs.fedoraproject.org/en-US/fedora-coreos/bare-metal/

### Git + Docker 
get repo subfolder with all compose files
```shell
mkdir git && cd git && \
git init && \
git remote add -f origin https://github.com/etancik/home-automation.git && \
git sparse-checkout init && \
git sparse-checkout add "central-server/docker-compose/" && \
git sparse-checkout add "central-server/initial-config/" && \
git pull origin master && \
cd ..
```

### Initial config for modules
```shell
mkdir ~/compose-volumes && cp -r ~/git/central-server/initial-config/* ~/compose-volumes
```

### Modules

#### MQTT
1. Start
```shell
docker-compose -f ~/git/central-server/docker-compose/mqtt.yml up -d
```
2. Add users
```shell
docker exec -it mqtt mosquitto_passwd -b /mosquitto/config/password.txt user password
```
3. Restart to apply new users
```shell
docker-compose -f ~/git/central-server/docker-compose/mqtt.yml restart
```
#### Homebridge
```shell
docker-compose -f ~/git/central-server/docker-compose/homebridge.yml up -d
```
#### Monitoring
```shell
docker-compose -f ~/git/central-server/docker-compose/monitoring.yml up -d
```

## List of ports

* 1883: mqtt
* 3000: grafana
* 8080: zigbee2mqtt 
* 8086: Influxdb HTTP service
* 8088: Influxdb RPC service
* 8581: HomeBridge
* 8888: ezsp for zigbee2mqtt