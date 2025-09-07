{
  "_metadata": {
    "mod_name": "BetterCrossbows",
    "version": "1.0",
    "description": "Règles spécifiques pour le mod BetterCrossbows",
    "author": "BG3 Translator",
    "extends": "base_bg3_rules.json"
  },

  "pre_translation": [
    {
      "name": "crossbow_loaded_state",
      "pattern": "\\bBolt Loaded\\b",
      "replacement": "CROSSBOW_LOADED_STATE",
      "description": "Protège l'état Carreau chargé"
    },
    {
      "name": "crossbow_unloaded_state", 
      "pattern": "\\bCrossbow Unloaded\\b",
      "replacement": "CROSSBOW_UNLOADED_STATE",
      "description": "Protège l'état Arbalète déchargée"
    },
    {
      "name": "load_bolt_action",
      "pattern": "\\bLoad Bolt\\b",
      "replacement": "LOAD_BOLT_ACTION",
      "description": "Protège l'action Charger un carreau"
    },
    {
      "name": "great_strike_action",
      "pattern": "\\bGreat Strike\\b", 
      "replacement": "GREAT_STRIKE_ACTION",
      "description": "Protège l'action Grande frappe"
    },
    {
      "name": "break_formation_action",
      "pattern": "\\bBreak Formation\\b",
      "replacement": "BREAK_FORMATION_ACTION", 
      "description": "Protège l'action Briser la formation"
    }
  ],

  "post_translation": [
    {
      "name": "fix_armor_wearers_intermediate",
      "pattern": "\\bporteurs d'armures intermédiaires\\b",
      "replacement": "porteurs d'armure intermédiaire",
      "description": "Corrige le pluriel pour armure intermédiaire"
    },
    {
      "name": "fix_armor_wearers_heavy",
      "pattern": "\\bporteurs d'armures lourdes\\b",
      "replacement": "porteurs d'armure lourde",
      "description": "Corrige le pluriel pour armure lourde"
    },
    {
      "name": "fix_bearer_conjugation",
      "pattern": "\\bLe porteur avez\\b",
      "replacement": "Le porteur a",
      "description": "Corrige la conjugaison pour 'le porteur'"
    },
    {
      "name": "fix_action_gender",
      "pattern": "\\bun action\\b",
      "replacement": "une action",
      "description": "Corrige le genre du mot action"
    },
    {
      "name": "fix_load_bolt_conjugation",
      "pattern": "\\bChargez un carreau\\b",
      "replacement": "Charge un carreau",
      "description": "Ajuste la conjugaison pour charger un carreau"
    },
    {
      "name": "fix_next_attack_gender",
      "pattern": "\\bSon prochaine attaque\\b",
      "replacement": "Sa prochaine attaque",
      "description": "Corrige l'accord de genre pour 'prochaine attaque'"
    },
    {
      "name": "fix_cost_structure",
      "pattern": "\\bne le porteur coûtera\\b",
      "replacement": "ne coûtera au porteur",
      "description": "Corrige la structure de phrase pour le coût"
    },
    {
      "name": "fix_action_point",
      "pattern": "\\bpoint d'action\\b",
      "replacement": "action",
      "description": "Simplifie 'point d'action' en 'action'"
    },
    {
      "name": "fix_before_attack",
      "pattern": "\\bavant une attaque\\b",
      "replacement": "avant de pouvoir attaquer",
      "description": "Améliore la formulation 'avant une attaque'"
    }
  ],

  "final_cleanup": [
    {
      "name": "restore_crossbow_loaded",
      "pattern": "\\bCROSSBOW_LOADED_STATE\\b",
      "replacement": "Carreau chargé",
      "description": "Restaure l'état Carreau chargé"
    },
    {
      "name": "restore_crossbow_unloaded",
      "pattern": "\\bCROSSBOW_UNLOADED_STATE\\b", 
      "replacement": "Arbalète déchargée",
      "description": "Restaure l'état Arbalète déchargée"
    },
    {
      "name": "restore_load_bolt",
      "pattern": "\\bLOAD_BOLT_ACTION\\b",
      "replacement": "Charger un carreau",
      "description": "Restaure l'action Charger un carreau"
    },
    {
      "name": "restore_great_strike",
      "pattern": "\\bGREAT_STRIKE_ACTION\\b",
      "replacement": "Grande frappe",
      "description": "Restaure l'action Grande frappe"
    },
    {
      "name": "restore_break_formation",
      "pattern": "\\bBREAK_FORMATION_ACTION\\b",
      "replacement": "Briser la formation",
      "description": "Restaure l'action Briser la formation"
    }
  ],

  "contextual_rules": [
    {
      "name": "crossbow_mechanics",
      "trigger_patterns": ["crossbow", "bolt", "carreau", "arbalète"],
      "rules": [
        {
          "pattern": "\\bloaded bolt\\b",
          "replacement": "carreau chargé",
          "description": "Traduction spécialisée pour les mécaniques d'arbalète"
        },
        {
          "pattern": "\\bunloaded crossbow\\b", 
          "replacement": "arbalète déchargée",
          "description": "État d'arbalète non chargée"
        }
      ]
    },
    {
      "name": "armor_targeting",
      "trigger_patterns": ["armor", "armure", "heavy", "medium"],
      "rules": [
        {
          "pattern": "\\bagainst heavy armor wearers\\b",
          "replacement": "contre les porteurs d'armure lourde",
          "description": "Ciblage des porteurs d'armure lourde"
        },
        {
          "pattern": "\\bagainst medium armor wearers\\b",
          "replacement": "contre les porteurs d'armure intermédiaire", 
          "description": "Ciblage des porteurs d'armure intermédiaire"
        }
      ]
    }
  ],

  "validation_rules": [
    {
      "name": "check_crossbow_consistency",
      "type": "consistency_check",
      "patterns": {
        "bolt": ["carreau", "Carreau"],
        "crossbow": ["arbalète", "Arbalète"],
        "loaded": ["chargé", "chargée"]
      },
      "description": "Vérifie la cohérence des termes d'arbalète"
    },
    {
      "name": "check_action_costs",
      "type": "grammar_check", 
      "pattern": "\\b(une|un) action\\b",
      "expected": "une action",
      "description": "Vérifie que 'action' est toujours féminin"
    }
  ],

  "learning_targets": [
    {
      "category": "weapon_mechanics",
      "patterns": ["bolt", "crossbow", "load", "charge"],
      "confidence_threshold": 0.9,
      "description": "Apprentissage des mécaniques d'armes à distance"
    },
    {
      "category": "armor_interactions", 
      "patterns": ["armor", "wearer", "target"],
      "confidence_threshold": 0.85,
      "description": "Apprentissage des interactions avec les armures"
    }
  ]
}