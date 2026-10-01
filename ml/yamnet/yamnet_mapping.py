"""
YAMNet Safety Event Mapping and Comprehensive AudioSet Taxonomy Engine.
Maps all 521 Google AudioSet classes into meaningful, assistive alert categories
with objective descriptions, strict priority arbitration, and hardware actuator mappings.
"""

from typing import Dict, Any, Optional

# Severity Levels and Priorities
# Priority 0: Physical SOS (Immediate Override)
# Priority 1: Critical Emergency (Life Safety, Hazards, Alarms) -> Hardware Strobe & WhatsApp
# Priority 2: Urgent Warning (Doorbell, Knock, Vehicle Hazards, Leaks) -> Yellow Pulse & Beep
# Priority 3: Informational (Animals, Household Appliances, Human Activity) -> Orange Solid, No Buzzer
# Priority 4: Normal / Ambient (Speech, Music, Environmental Acoustics) -> Blue Breath, No Buzzer
PRIORITY_MAP = {
    "SOS": 0,
    "CRITICAL": 1,
    "WARNING": 2,
    "INFO": 3,
    "NORMAL": 4
}

# Semantic Category Mappings
SAFETY_CATEGORIES: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------
    # 0. PHYSICAL SOS
    # -------------------------------------------------------------
    "SOS": {
        "displayLabel": "Physical Emergency SOS",
        "description": "Direct manual trigger from ESP32 emergency button or Dashboard SOS.",
        "severity": "SOS",
        "priority": 0,
        "notificationRequired": True,
        "rgbColor": [255, 0, 128],       # Red + Magenta Strobe
        "rgbMode": "EMERGENCY_STROBE",
        "lcdLine1": "!!! SOS !!!",
        "lcdLine2": "HELP NEEDED",
        "buzzerPattern": "SOS_ALARM",
        "keywords": ["sos", "manual_button", "emergency button"]
    },

    # -------------------------------------------------------------
    # 1. CRITICAL EMERGENCY (Priority 1)
    # -------------------------------------------------------------
    "SMOKE_FIRE_ALARM": {
        "displayLabel": "Smoke / Fire Alarm Detected",
        "description": "Continuous high-pitch safety alarm or residential smoke detector.",
        "severity": "CRITICAL",
        "priority": 1,
        "notificationRequired": True,
        "rgbColor": [255, 0, 0],         # Blazing Crimson Red
        "rgbMode": "RED_STROBE",
        "lcdLine1": "CRITICAL ALERT",
        "lcdLine2": "Fire / Smoke",
        "buzzerPattern": "CRITICAL_ALARM",
        "keywords": ["smoke detector, smoke alarm", "fire alarm"]
    },
    "ALARM": {
        "displayLabel": "Alarm Detected",
        "description": "High-decibel emergency siren, civil defense siren, or building alarm.",
        "severity": "CRITICAL",
        "priority": 1,
        "notificationRequired": True,
        "rgbColor": [255, 0, 40],        # Vivid Siren Red
        "rgbMode": "RED_STROBE",
        "lcdLine1": "CRITICAL ALERT",
        "lcdLine2": "Alarm Detected",
        "buzzerPattern": "CRITICAL_ALARM",
        "keywords": ["alarm", "siren", "civil defense siren", "car alarm", "police car (siren)", "ambulance (siren)", "fire engine, fire truck (siren)", "foghorn"]
    },
    "DISTRESS": {
        "displayLabel": "Distress / Screaming Detected",
        "description": "Vocal screaming, high-intensity distress, yelling, or infant crying.",
        "severity": "CRITICAL",
        "priority": 1,
        "notificationRequired": True,
        "rgbColor": [255, 20, 147],      # Deep Urgent Rose-Magenta
        "rgbMode": "MAGENTA_PULSE",
        "lcdLine1": "CRITICAL ALERT",
        "lcdLine2": "Distress Sound",
        "buzzerPattern": "CRITICAL_ALARM",
        "keywords": ["screaming", "shout", "yell", "children shouting", "bellow", "whoop", "crying, sobbing", "baby cry, infant cry", "wail, moan"]
    },
    "GLASS_BREAK": {
        "displayLabel": "Possible Glass Break",
        "description": "High-frequency shatter or impact sound resembling breaking glass.",
        "severity": "CRITICAL",
        "priority": 1,
        "notificationRequired": True,
        "rgbColor": [255, 30, 60],       # Shimmering Ruby Red
        "rgbMode": "GLASS_SPARKLE",
        "lcdLine1": "WARNING",
        "lcdLine2": "Glass Break",
        "buzzerPattern": "CRITICAL_ALARM",
        "keywords": ["glass", "shatter", "chink, clink", "crushing", "splinter"]
    },
    "EXPLOSION_GUNSHOT": {
        "displayLabel": "Explosion / Gunshot Detected",
        "description": "High-energy impulse shockwave, gunshot, blast, or fireworks detonation.",
        "severity": "CRITICAL",
        "priority": 1,
        "notificationRequired": True,
        "rgbColor": [255, 255, 255],     # Brilliant Flash White
        "rgbMode": "EMERGENCY_STROBE",
        "lcdLine1": "CRITICAL ALERT",
        "lcdLine2": "Explosion/Shot",
        "buzzerPattern": "CRITICAL_ALARM",
        "keywords": ["explosion", "gunshot, gunfire", "machine gun", "fusillade", "artillery fire", "cap gun", "fireworks", "firecracker", "burst, pop", "eruption", "boom"]
    },

    # -------------------------------------------------------------
    # 2. URGENT WARNING (Priority 2)
    # -------------------------------------------------------------
    "DOORBELL": {
        "displayLabel": "Doorbell / Chime",
        "description": "Door chime, entrance bell, or ding-dong alert.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [255, 185, 0],       # Warm Honey Gold
        "rgbMode": "YELLOW_PULSE",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Doorbell",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["doorbell", "ding-dong", "chime", "jingle bell", "bicycle bell", "church bell", "bell", "tuning fork", "wind chime"]
    },
    "KNOCK": {
        "displayLabel": "Door Knock / Tap",
        "description": "Rhythmic rap, door knocking, or surface tapping.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [255, 125, 0],       # Tangerine Amber
        "rgbMode": "YELLOW_FLASH",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Knock on Door",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["knock", "tap", "slam", "thump, thud", "thunk", "door"]
    },
    "VEHICLE_HAZARD": {
        "displayLabel": "Vehicle Horn / Road Hazard",
        "description": "Car horn, air horn, tire screech, skidding, or train horn.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [255, 160, 0],       # Caution Amber
        "rgbMode": "YELLOW_PULSE",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Vehicle Horn",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["vehicle horn, car horn, honking", "air horn, truck horn", "skidding", "tire squeal", "car passing by", "race car, auto racing", "reversing beeps", "train whistle", "train horn", "train wheels squealing", "engine knocking"]
    },
    "POWER_TOOL": {
        "displayLabel": "Power Tool / Machinery",
        "description": "Active power tool, drill, chainsaw, lawn mower, or mechanical saw.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [255, 140, 20],      # Industrial Orange-Amber
        "rgbMode": "YELLOW_SOLID",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Power Tool",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["power tool", "drill", "chainsaw", "lawn mower", "jackhammer", "sawing", "hammer", "pneumatic tool"]
    },
    "HEALTH_HAZARD": {
        "displayLabel": "Severe Coughing / Choking",
        "description": "Heavy coughing, choking, throat clearing, or acute respiratory distress.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [255, 90, 160],      # Respiratory Rose Pink
        "rgbMode": "MAGENTA_PULSE",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Coughing/Gasp",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["cough", "throat clearing", "sneeze", "gasp", "pant", "snort", "wheeze"]
    },
    "DOMESTIC_WATER": {
        "displayLabel": "Water Running / Domestic Flow",
        "description": "Water tap running, sink overflowing, flush, or rapid liquid gush.",
        "severity": "WARNING",
        "priority": 2,
        "notificationRequired": False,
        "rgbColor": [0, 220, 255],       # Deep Aquamarine / Cyan
        "rgbMode": "CYAN_BREATH",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Water Running",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["water tap, faucet", "sink (filling or washing)", "bathtub", "shower", "toilet flush", "gush", "pour", "drip", "boiling", "sizzle"]
    },

    # -------------------------------------------------------------
    # 3. INFORMATIONAL SOUNDS (Priority 3)
    # -------------------------------------------------------------
    "DOG_BARK": {
        "displayLabel": "Dog Bark",
        "description": "Canine barking, vocalization, or howling.",
        "severity": "INFO",
        "priority": 3,
        "notificationRequired": False,
        "rgbColor": [175, 55, 255],      # Electric Violet
        "rgbMode": "PURPLE_GLOW",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Dog Bark",
        "buzzerPattern": "MODERATE_BEEP",
        "keywords": ["dog", "bark", "bow-wow", "yip", "howl", "growling", "whimper (dog)"]
    },
    "ANIMAL_SOUND": {
        "displayLabel": "Animal Vocalization",
        "description": "Cat meowing, bird vocalization, or other domestic pet sounds.",
        "severity": "INFO",
        "priority": 3,
        "notificationRequired": False,
        "rgbColor": [195, 75, 255],      # Radiant Orchid Violet
        "rgbMode": "PURPLE_GLOW",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Animal Vocal",
        "buzzerPattern": "OFF",
        "keywords": ["cat", "purr", "meow", "hiss", "caterwaul", "bird", "bird vocalization, bird call, bird song", "chirp, tweet", "squawk", "crowing, cock-a-doodle-doo", "quack", "honk", "livestock, farm animals, working animals", "horse", "cowbell", "pig", "oink", "goat", "bleat", "sheep", "chicken, rooster"]
    },
    "CLAPPING": {
        "displayLabel": "Clapping / Applause",
        "description": "Hand clapping, cheering, or audience applause.",
        "severity": "INFO",
        "priority": 3,
        "notificationRequired": False,
        "rgbColor": [255, 145, 75],      # Warm Peach Gold
        "rgbMode": "PEACH_SPARKLE",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Clapping",
        "buzzerPattern": "OFF",
        "keywords": ["clapping", "applause", "cheering", "finger snapping"]
    },
    "HUMAN_SOUND": {
        "displayLabel": "Human Activity",
        "description": "Laughter, footstep patter, clearing throat, or domestic human sounds.",
        "severity": "INFO",
        "priority": 3,
        "notificationRequired": False,
        "rgbColor": [255, 130, 90],      # Coral Peach
        "rgbMode": "PEACH_SPARKLE",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Human Sound",
        "buzzerPattern": "OFF",
        "keywords": ["laughter", "baby laughter", "giggle", "snicker", "belly laugh", "chuckle, chortle", "sigh", "yawn", "snore", "footsteps", "patter", "chewing, mastication", "whispering"]
    },
    "APPLIANCE": {
        "displayLabel": "Household Appliance / Ring",
        "description": "Telephone ringing, microwave, blender, vacuum cleaner, or clock tick.",
        "severity": "INFO",
        "priority": 3,
        "notificationRequired": False,
        "rgbColor": [215, 95, 255],      # Soft Orchid Lavender
        "rgbMode": "PURPLE_GLOW",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": "Appliance/Ring",
        "buzzerPattern": "OFF",
        "keywords": ["telephone", "telephone bell ringing", "ringtone", "cellphone buzz, vibration", "alarm clock", "buzzer", "microwave oven", "blender", "vacuum cleaner", "hair dryer", "computer keyboard", "typewriter", "clock", "tick", "tick-tock"]
    },

    # -------------------------------------------------------------
    # 4. NORMAL / AMBIENT (Priority 4)
    # -------------------------------------------------------------
    "SPEECH": {
        "displayLabel": "Speech",
        "description": "Human conversation, monologue, or voice.",
        "severity": "NORMAL",
        "priority": 4,
        "notificationRequired": False,
        "rgbColor": [0, 160, 255],       # Ocean Sky Blue
        "rgbMode": "BLUE_BREATH",
        "lcdLine1": "LISTENING...",
        "lcdLine2": "Speech",
        "buzzerPattern": "OFF",
        "keywords": ["speech", "child speech, kid speaking", "conversation", "narration, monologue", "babbling", "chatter", "crowd", "hubbub"]
    },
    "MUSIC": {
        "displayLabel": "Music",
        "description": "Instrumental or melodic audio, singing, guitar, piano, or rhythm.",
        "severity": "NORMAL",
        "priority": 4,
        "notificationRequired": False,
        "rgbColor": [75, 105, 255],      # Electric Indigo
        "rgbMode": "INDIGO_CHASE",
        "lcdLine1": "LISTENING...",
        "lcdLine2": "Music",
        "buzzerPattern": "OFF",
        "keywords": ["music", "musical instrument", "singing", "choir", "guitar", "electric guitar", "bass guitar", "acoustic guitar", "piano", "electric piano", "organ", "synthesizer", "drum kit", "drum", "snare drum", "tabla", "cymbal", "hi-hat", "violin, fiddle", "cello", "flute", "saxophone", "trumpet", "trombone", "harp", "harmonica", "rock music", "pop music", "hip hop music", "jazz", "classical music", "electronic music"]
    },
    "NORMAL": {
        "displayLabel": "Silence / Normal",
        "description": "Ambient environmental silence or neutral acoustic background.",
        "severity": "NORMAL",
        "priority": 4,
        "notificationRequired": False,
        "rgbColor": [255, 255, 255],     # Pure Ambient White
        "rgbMode": "WHITE_BREATH",
        "lcdLine1": "LISTENING...",
        "lcdLine2": "Silence/Normal",
        "buzzerPattern": "OFF",
        "keywords": ["silence", "noise", "environmental noise", "inside, small room", "inside, large room or hall", "white noise", "pink noise", "mechanical fan", "air conditioning", "background noise"]
    }
}


def map_yamnet_label_to_safety_event(label: str) -> Dict[str, Any]:
    """
    Search safety categories for match against raw AudioSet label.
    Preserves exact detected label for rich UI awareness while categorizing safely.
    """
    if not label:
        return {
            "category": "NORMAL",
            **SAFETY_CATEGORIES["NORMAL"],
            "displayLabel": "Monitoring",
            "rawLabel": ""
        }

    lower_label = label.lower().strip()
    
    # Priority ordered category evaluation
    category_order = [
        "SOS",
        "SMOKE_FIRE_ALARM",
        "ALARM",
        "DISTRESS",
        "GLASS_BREAK",
        "EXPLOSION_GUNSHOT",
        "DOORBELL",
        "KNOCK",
        "VEHICLE_HAZARD",
        "POWER_TOOL",
        "HEALTH_HAZARD",
        "DOMESTIC_WATER",
        "DOG_BARK",
        "ANIMAL_SOUND",
        "CLAPPING",
        "APPLIANCE",
        "HUMAN_SOUND",
        "SPEECH",
        "MUSIC",
        "NORMAL"
    ]
    
    for cat_key in category_order:
        cat_data = SAFETY_CATEGORIES.get(cat_key)
        if not cat_data:
            continue
        for kw in cat_data["keywords"]:
            if kw in lower_label:
                # Use clean capitalized version of detected sound for informative UI label
                clean_display = label.strip()
                if cat_data["severity"] in ("CRITICAL", "SOS"):
                    display_title = cat_data["displayLabel"]
                else:
                    display_title = clean_display

                # Truncate LCD line 2 to 16 chars max
                lcd_l2 = clean_display[:16]
                
                return {
                    "category": cat_key,
                    "displayLabel": display_title,
                    "rawLabel": label,
                    "description": cat_data["description"],
                    "severity": cat_data["severity"],
                    "priority": cat_data["priority"],
                    "notificationRequired": cat_data["notificationRequired"],
                    "rgbColor": cat_data["rgbColor"],
                    "rgbMode": cat_data["rgbMode"],
                    "lcdLine1": cat_data["lcdLine1"],
                    "lcdLine2": lcd_l2,
                    "buzzerPattern": cat_data["buzzerPattern"]
                }
                
    # If not in explicit list, provide rich unmapped awareness (don't mask as "Monitoring")
    clean_name = label.strip()
    return {
        "category": "NORMAL",
        "displayLabel": clean_name,
        "rawLabel": label,
        "description": f"AudioSet acoustic classification: {clean_name}",
        "severity": "NORMAL",
        "priority": 4,
        "notificationRequired": False,
        "rgbColor": [255, 255, 255],
        "rgbMode": "WHITE_BREATH",
        "lcdLine1": "SOUND DETECTED",
        "lcdLine2": clean_name[:16],
        "buzzerPattern": "OFF"
    }
