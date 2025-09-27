# ESPlan Enclosure Modifications for CO2 Sensor

## Original 3D Files
- **ESPlan.step** - CAD model for modifications
- **ESPlan_case.3mf** - 3D printable case (latest with hole fixes)

## Required Modifications for CO2 + OLED Setup

### 1. **Front Panel Modifications**

#### **OLED Display Window**
- **Location**: Center-front of enclosure
- **Size**: 26mm x 19mm rectangular cutout
- **Depth**: 2mm recess for flush mounting
- **Protection**: Consider clear acrylic window (optional)

#### **SCD41 Ventilation**
- **Location**: Below or beside OLED window
- **Pattern**: Grid of 2mm diameter holes
- **Spacing**: 4mm centers (2mm hole, 2mm gap)
- **Area**: 20mm x 10mm grid (2x5 holes = 10 holes total)
- **Purpose**: Allow air circulation for CO2 measurement

### 2. **Internal Layout Considerations**

#### **Component Spacing**
```
ESPlan Board (existing)
    ↓ μŠup connectors
OLED Display ← → SCD41 Sensor
    ↓
Front panel mounting
```

#### **Cable Management**
- **μŠup connectors**: Short cables to sensors (~50mm)
- **Strain relief**: Small slots for cable entry if needed
- **Routing**: Keep cables away from ethernet connector

### 3. **Mounting Solutions**

#### **OLED Display Mounting**
- **Location**: Center-front of enclosure
- **Size**: 26mm x 19mm rectangular cutout
- **Depth**: 2mm recess for flush mounting
- **Protection**: Consider clear acrylic window (optional)

#### **SCD41 Ventilation**
- **Location**: Below or beside OLED window
- **Pattern**: Grid of 2mm diameter holes
- **Spacing**: 4mm centers (2mm hole, 2mm gap)
- **Area**: 20mm x 10mm grid (2x5 holes = 10 holes total)
- **Purpose**: Allow air circulation for CO2 measurement

### 2. **Internal Layout Considerations**

#### **Component Spacing**
```
ESPlan Board (existing)
    ↓ μŠup connectors
OLED Display ← → SCD41 Sensor
    ↓
Front panel mounting
```

#### **Cable Management**
- **μŠup connectors**: Short cables to sensors (~50mm)
- **Strain relief**: Small slots for cable entry if needed
- **Routing**: Keep cables away from ethernet connector

### 3. **Mounting Solutions**

#### **OLED Display Mounting**
- **Option A**: Hot-glue directly to front panel recess
- **Option B**: Small bracket with M2 screws
- **Alignment**: Ensure display is centered in cutout

#### **SCD41 Sensor Mounting**
- **Position**: Behind ventilation holes
- **Method**: Double-sided foam tape or small bracket
- **Orientation**: Sensor intake facing ventilation holes

### 4. **3D Printing Modifications Needed**

#### **Files to Modify**
1. **ESPlan_case.3mf** - Main enclosure
2. Create custom front panel if needed

#### **CAD Software Options**
- **Fusion 360** (free for personal use)
- **FreeCAD** (open source)
- **Tinkercad** (browser-based, simple)
- **PrusaSlicer** (can modify 3MF files directly)

#### **Modification Steps**
1. Import ESPlan_case.3mf
2. Add OLED rectangular cutout (26x19mm)
3. Add ventilation hole pattern (10x 2mm holes)
4. Optional: Add cable management slots
5. Test print and fit-check

### 5. **Alternative: External Sensor Mount**

#### **If Internal Space is Limited**
- **OLED**: Inside enclosure, visible through window
- **SCD41**: External mount with longer μŠup cable
- **Benefits**: Better air circulation, easier access
- **Drawbacks**: More complex mounting, weather protection needed

### 6. **Modification Templates**

#### **OLED Window Dimensions**
```
Width: 26mm
Height: 19mm
Corner radius: 1mm
Depth: 2mm recess
Position: Center of front panel
```

#### **Ventilation Pattern**
```
Hole diameter: 2mm
Hole spacing: 4mm centers
Pattern: 2 rows x 5 columns
Total area: 16mm x 8mm
Position: 10mm below OLED window
```

### 7. **Assembly Order**
1. Install ESPlan board in enclosure
2. Connect μŠup cables to OLED and SCD41
3. Mount OLED in front panel cutout
4. Position SCD41 behind ventilation holes
5. Route cables neatly
6. Close enclosure and test

### 8. **Testing Checklist**
- [ ] OLED visible and readable through window
- [ ] SCD41 has adequate air flow
- [ ] All connections secure
- [ ] Ethernet connector accessible
- [ ] Power LED visible (if desired)
- [ ] Easy to disassemble for maintenance

## Tools Needed for Modification
- **3D Printer** or **3D printing service**
- **CAD software** (see options above)
- **Calipers** for precise measurements
- **Small files/sandpaper** for finishing
- **Hot glue gun** or **double-sided tape** for mounting

## Ready-to-Use Dimensions
All measurements provided above are ready for direct use in CAD software. The modifications are minimal and should maintain the structural integrity of the original enclosure design.

Would you like me to create more detailed technical drawings or provide specific instructions for any particular CAD software?