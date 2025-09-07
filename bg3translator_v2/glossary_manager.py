"""
Gestionnaire de glossaire pour la traduction de mods BG3
Centralise tous les termes de traduction extraits du script original
"""

from typing import Dict, List, Tuple
import re
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GlossaryManager:
    """Gestionnaire centralisé du glossaire de traduction"""
    
def learn_from_llm_improvement(self, original_text: str, deepl_translation: str, llm_improvement: str):
    """Analyse et apprend des améliorations LLM pour enrichir le glossaire"""
    
    # Ignore si pas d'amélioration significative
    if deepl_translation == llm_improvement or len(llm_improvement.strip()) == 0:
        return False
    
    # Détecte les améliorations de termes spécifiques
    improvements_found = []
    
    # Recherche de patterns d'amélioration courants
    patterns = [
        # Corrections de genre/nombre
        (r'\b(\d+) dégâts\b', r'\1 points de dégâts'),
        (r'\b1 dégâts\b', '1 point de dégât'),
        
        # Améliorations terminologiques
        (r'\battaquez\b', 'tirez sur'),  # pour les armes à distance
        (r'\bgrande grève\b', 'grande frappe'),
        (r'\binfligeant éventuellement\b', 'pouvant infliger'),
        
        # Corrections de casse après ponctuation
        (r'\. ([a-z])', lambda m: '. ' + m.group(1).upper()),
    ]
    
    # Compare les différences significatives
    deepl_words = set(deepl_translation.lower().split())
    llm_words = set(llm_improvement.lower().split())
    
    # Si le LLM a remplacé des mots spécifiques
    different_words = deepl_words.symmetric_difference(llm_words)
    
    if different_words and len(different_words) <= 6:  # Changements mineurs mais significatifs
        # Extrait les améliorations potentielles
        for deepl_word in deepl_words:
            if deepl_word not in llm_words and len(deepl_word) > 3:
                # Trouve le mot de remplacement potentiel
                for llm_word in llm_words:
                    if llm_word not in deepl_words and len(llm_word) > 3:
                        # Ajoute comme amélioration potentielle
                        self._glossary[deepl_word] = llm_word
                        improvements_found.append((deepl_word, llm_word))
                        logger.info(f"Apprentissage LLM: '{deepl_word}' -> '{llm_word}'")
                        break
    
    return len(improvements_found) > 0

    def __init__(self):
        self._glossary = {}
        self._load_main_glossary()
    
    def _load_main_glossary(self):
        """Charge le glossaire principal extrait du script original"""
        self._glossary = MAIN_GLOSSARY.copy()
    
    def get_glossary(self) -> Dict[str, str]:
        """Retourne le glossaire complet trié par longueur décroissante"""
        return dict(sorted(self._glossary.items(), key=lambda x: -len(x[0])))
    
    def add_terms(self, terms: Dict[str, str]):
        """Ajoute des termes dynamiquement"""
        self._glossary.update(terms)
    
    def save_to_main_glossary(self, filepath: str = None):
        """Sauvegarde les termes dans le glossaire principal"""
        if filepath is None:
            # Trouver le chemin du fichier actuel
            filepath = Path(__file__).resolve()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Trouver la position de MAIN_GLOSSARY
            start_idx = content.find("MAIN_GLOSSARY = {")
            if start_idx == -1:
                logger.error("Impossible de trouver MAIN_GLOSSARY dans le fichier")
                return False
            
            # Trouver la fin du dictionnaire MAIN_GLOSSARY
            brace_count = 0
            end_idx = start_idx
            for i, char in enumerate(content[start_idx:]):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = start_idx + i + 1
                        break
            
            if brace_count != 0:
                logger.error("Structure de MAIN_GLOSSARY invalide")
                return False
            
            # Construire le nouveau contenu du glossaire
            new_glossary = "MAIN_GLOSSARY = {\n"
            for term, translation in sorted(self._glossary.items()):
                # Échapper les guillemets dans les traductions
                translation_escaped = translation.replace('"', '\\"')
                new_glossary += f'    "{term}": "{translation_escaped}",\n'
            new_glossary += "}"
            
            # Remplacer l'ancien glossaire par le nouveau
            new_content = content[:start_idx] + new_glossary + content[end_idx:]
            
            # Sauvegarder le fichier modifié
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Glossaire principal mis à jour dans {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du glossaire principal: {e}")
            return False
    
    def save_custom_terms(self, filepath: str):
        """Sauvegarde les termes personnalisés"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._glossary, f, ensure_ascii=False, indent=2)
    
    def load_custom_terms(self, filepath: str):
        """Charge des termes personnalisés depuis un fichier"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                custom_terms = json.load(f)
                self._glossary.update(custom_terms)
                logger.info(f"Chargé {len(custom_terms)} termes personnalisés depuis {filepath}")
        except FileNotFoundError:
            logger.warning(f"Fichier de termes personnalisés non trouvé: {filepath}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des termes personnalisés: {e}")

# ===== GLOSSAIRE PRINCIPAL EXTRAIT DU SCRIPT ORIGINAL =====
MAIN_GLOSSARY = {
    # Termes de base et mécaniques de jeu
    "Ability Check": "Test de caractéristique",
    "Ability Score": "Score de caractéristique",
    "Action": "Action",
    "Action Point": "Point d'action",
    "Advantage": "Avantage",
    "Armor Class": "Classe d'armure",
    "Attack Roll": "Jet d'attaque",
    "Bonus Action": "Action bonus",
    "Challenge Rating": "Indice de dangerosité",
    "Character Level": "Niveau de personnage",
    "Class": "Classe",
    "Concentration": "Concentration",
    "Damage Roll": "Jet de dégâts",
    "Difficulty Class": "Degré de difficulté",
    "Disadvantage": "Désavantage",
    "Experience Points": "Points d'expérience",
    "Hit Points": "Points de vie",
    "HP": "PV",
    "Initiative": "Initiative",
    "Proficiency": "Maîtrise",
    "Reaction": "Réaction",
    "Saving Throw": "Jet de sauvegarde",
    "Skill Check": "Test de compétence",
    "Spell Slot": "Emplacement de sort",
    "Health": "Points de vie",
    "Movement Points": "Mouvement",
    "Shield Bearer": "Porteur de bouclier",
    "Deal": "Infliger",
    "Fire at": "Tirer sur",
    "Silence": "Rendre muet",
    "Grapple": "Agripper",
    "Disarm": "Désarmer",
    "Fear": "Peur",
    
    # Types de dégâts
    "Acid Damage": "Dégâts d'acide",
    "Bludgeoning Damage": "Dégâts contondants",
    "Cold Damage": "Dégâts de froid",
    "Fire Damage": "Dégâts de feu",
    "Force Damage": "Dégâts de force",
    "Lightning Damage": "Dégâts de foudre",
    "Necrotic Damage": "Dégâts nécrotiques",
    "Piercing Damage": "Dégâts perforants",
    "Poison Damage": "Dégâts de poison",
    "Psychic Damage": "Dégâts psychiques",
    "Radiant Damage": "Dégâts radieux",
    "Slashing Damage": "Dégâts tranchants",
    "Thunder Damage": "Dégâts de tonnerre",
    
    # Types d'armures
    "Light Armor": "Armure légère",
    "Medium Armor": "Armure intermédiaire",
    "Heavy Armor": "Armure lourda",
    "Unarmored": "Sans armure",
    "Natural Armor": "Armure naturelle",
    
    # Écoles de magie
    "Abjuration": "Abjuration",
    "Conjuration": "Invocation",
    "Divination": "Divination",
    "Enchantment": "Enchantement",
    "Evocation": "Évocation",
    "Illusion": "Illusion",
    "Necromancy": "Nécromancie",
    "Transmutation": "Transmutation",
    
    # États et conditions
    "Blinded": "Aveuglé",
    "Charmed": "Charmé",
    "Deafened": "Sourd",
    "Exhaustion": "Épuisement",
    "Frightened": "Terrifié",
    "Grappled": "Agrippé",
    "Incapacitated": "Incapacité",
    "Invisible": "Invisible",
    "Paralyzed": "Paralysé",
    "Petrified": "Pétrifié",
    "Poisoned": "Empoisonné",
    "Prone": "À terre",
    "Restrained": "Entravé",
    "Stunned": "Étourdi",
    "Unconscious": "Inconscient",
    
    # Races et peuples
    "Dwarf": "Nain",
    "Elf": "Elfe",
    "Halfling": "Halfelin",
    "Human": "Humain",
    "Dragonborn": "Drakéide",
    "Gnome": "Gnome",
    "Half-Elf": "Demi-elfe",
    "Half-Orc": "Demi-orc",
    "Tiefling": "Tieffelin",
    "Githyanki": "Githyanki",
    "Drow": "Drow",
    "Hill Dwarf": "Nain des collines",
    
    # Classes
    "Barbarian": "Barbare",
    "Bard": "Barde",
    "Cleric": "Clerc",
    "Druid": "Druide",
    "Fighter": "Guerrier",
    "Monk": "Moine",
    "Paladin": "Paladin",
    "Ranger": "Rôdeur",
    "Rogue": "Roublard",
    "Sorcerer": "Ensorceleur",
    "Warlock": "Occultiste",
    "Wizard": "Magicien",
    
    # Équipement et objets
    "Potion": "Potion",
    "Scroll": "Parchemin",
    "Wand": "Baguette",
    "Staff": "Bâton",
    "Rod": "Baguette",
    "Amulet": "Amulette",
    "Ring": "Bague",
    "Cloak": "Cape",
    "Boots": "Bottes",
    "Gloves": "Gants",
    "Helmet": "Heaume",
    "Shield": "Bouclier",
    "Weapon": "Arme",
    "Armor": "Armure",
    "Rapier": "Rapière",
    "Warhammer": "Marteau de guerre",
    "Battleaxe": "Hache de bataille",
    "Bow": "Arc",
    
    # Termes spécifiques à BG3
    "Tadpole": "Têtard",
    "Illithid": "Illithid",
    "Mind Flayer": "Flagelleur mental",
    "Absolute": "Absolute",
    "True Soul": "Véritable âme",
    "Tav": "Tav",
    "Lae'zel": "Lae'zel",
    "Shadowheart": "Shadowheart",
    "Astarion": "Astarion",
    "Gale": "Gale",
    "Wyll": "Wyll",
    "Karlach": "Karlach",
    
    # Actions et capacités courantes
    "Attack": "Attaquer",
    "Cast a Spell": "Lancer un sort",
    "Dash": "Célérité",
    "Disengage": "Désengagement",
    "Dodge": "Esquive",
    "Help": "Aider",
    "Hide": "Se cacher",
    "Ready": "Se préparer",
    "Search": "Fouiller",
    "Use an Object": "Utiliser un objet",
    "Parry": "Parer",
    "Disarm": "Désarmer",
    "Pick Scab": "Entaille infectée",
    "Stone Striker": "Frappe-pierre",
    "Fury": "Fureur",
    "Finishing Spike": "Coup de grâce",
    "Magnificent Smash": "Écrasement magistral",
    "Heavy Metal": "Briseur de plates",
    "hit hard": "frapper fort",
    "bleeding": "hémorragie",
    "treat half your weapon damage": "convertir la moitié de vos dégâts",
    "armed damage": "dégâts",
    "Accept the Challenge": "Accepter le défi",
    "Death Before Dishonor": "Mort avant le déshonneur",
    "Nowhere to Hide": "Nulle part à se cacher",
    "Nowhere to Run": "Nulle part à courir",
    "Grappling Strike": "Frappe des grappins",
    "Hook Shield": "Bouclier à crochet",
    "Spike Strike": "Frappe des pointes",
    "Swift Shot": "Coup rapide",
    "Rapid Shot": "Tir rapide",
    "Titan String": "Corde de titan",
    "Max String": "Corde maximale",
    
    # Expressions temporelles
    "for one turn": "pendant un tour",
    "until the end of your next turn": "jusqu'à la fin de votre prochain tour",
    "until the start of your next turn": "jusqu'au début de votre prochain tour",
    "until the end of combat": "jusqu'à la fin du combat",
    "until dispelled": "jusqu'à dissipation",
    "until long rest": "jusqu'au prochain repos long",
    "once per combat": "une fois par combat",
    
    # Expressions de comparaison
    "vs": "contre",
    "versus": "contre",
    "within": "dans un rayon de",
    "range": "portée",
    "radius": "rayon",
    
    # Termes de dégâts et soins
    "additional damage": "dégâts supplémentaires",
    "extra damage": "dégâts supplémentaires",
    "healing": "soins",
    "temporary hit points": "points de vie temporaires",
    "maximum hit points": "points de vie maximum",
    
    # Termes magiques
    "spell save DC": "DD de sauvegarde du sort",
    "spell attack modifier": "modificateur d'attaque de sort",
    "spellcasting ability": "caractéristique d'incantation",
    "ritual spell": "sort rituel",
    "cantrip": "tour de magie",
    
    # Termes d'équipement avancés
    "martial weapon": "arme de guerre",
    "simple weapon": "arme simple",
    "finesse weapon": "arme fine",
    "versatile weapon": "arme polyvalente",
    "heavy weapon": "arme lourde",
    "light weapon": "arme légère",
    "reach weapon": "arme allongée",
    "thrown weapon": "arme de lancer",
    "magical weapon": "arme magique",
    "silvered weapon": "arme argentée",
    
    # Expressions de localisation
    "melee weapon attack": "attaque d'arme au corps à corps",
    "ranged weapon attack": "attaque d'arme à distance",
    "melee spell attack": "attaque de sort au corps à corps",
    "ranged spell attack": "attaque de sort à distance",
    "self": "personnelle",
    "touch": "contact",
    
    # Termes de caractéristiques
    "Strength": "Force",
    "Dexterity": "Dextérité",
    "Constitution": "Constitution",
    "Intelligence": "Intelligence",
    "Wisdom": "Sagesse",
    "Charisma": "Charisme",
    
    # Compétences
    "Acrobatics": "Acrobaties",
    "Animal Handling": "Dressage",
    "Arcana": "Arcanes",
    "Athletics": "Athlétisme",
    "Deception": "Tromperie",
    "History": "Histoire",
    "Insight": "Perspicacité",
    "Intimidation": "Intimidation",
    "Investigation": "Investigation",
    "Medicine": "Médecine",
    "Nature": "Nature",
    "Perception": "Perception",
    "Performance": "Représentation",
    "Persuasion": "Persuasion",
    "Religion": "Religion",
    "Sleight of Hand": "Escamotage",
    "Stealth": "Discrétion",
    "Survival": "Survie",
    
    # Expressions de ciblage
    "target": "cible",
    "creature": "créature",
    "ally": "allié",
    "enemy": "ennemi",
    "hostile": "hostile",
    "friendly": "ami",
    "neutral": "neutre",
    
    # Expressions de résistance et immunité
    "resistance": "résistance",
    "immunity": "immunité",
    "vulnerability": "vulnérabilité",
    
    # Expressions de jet
    "roll": "jet",
    "dice": "dé",
    "die": "dé",
    "check": "test",
    "save": "sauvegarde",
    
    # Termes de sorts courants
    "Cantrip": "Tour de magie",
    "Level 1 Spell": "Sort de niveau 1",
    "Level 2 Spell": "Sort de niveau 2",
    "Level 3 Spell": "Sort de niveau 3",
    "Level 4 Spell": "Sort de niveau 4",
    "Level 5 Spell": "Sort de niveau 5",
    "Level 6 Spell": "Sort de niveau 6",
    
    # Expressions de durée
    "instantaneous": "instantané",
    "1 round": "1 round",
    "1 minute": "1 minute",
    "10 minutes": "10 minutes",
    "1 hour": "1 heure",
    "8 hours": "8 heures",
    "24 hours": "24 heures",
    
    # Autres termes courants
    "charges": "charges",
    "cooldown": "temps de recharge",
    "per day": "par jour",
    "per short rest": "par repos court",
    "per long rest": "par repos long",
    
    # Expressions spécifiques de BG3
    "Illithid Power": "Pouvoir illithid",
    "Tadpole Power": "Pouvoir de têtard",
    "Dialogue Option": "Option de dialogue",
    "Skill Check Required": "Test de compétence requis",
    "Persuasion Check": "Test de persuasion",
    "Intimidation Check": "Test d'intimidation",
    "Deception Check": "Test de tromperie",
    
    # Termes spécifiques au mod
    "Do 1d6 additional damage vs Medium Armour": "Inflige 1d6 de dégâts supplémentaires contre les porteurs d'armures intermédiaires",
    "-1 to AC for one turn": "Subit un malus de -1 à la CA jusqu'à la fin du tour suivant",
    "Mail Mangler": "Broyeur de mailles",
    "Rend Armour": "Brèche d'armure",
    "AC": "CA",
    "Medium Armour": "armure intermédiaire",
    "Damage": "dégâts",
    "-4 to Intelligence and Wisdom": "Subit un malus de -4 à l'Intelligence et à la Sagesse",
    "Concussed": "Étourdi",
    "If the target is not wearing Heavy Armor, try to bash their head in, Concussing them": "Si la cible ne porte pas d'armure lourde, tentez une attaque à la tête, l'étourdissant jusqu'à la fin du tour suivant.",
    "Stove in Head": "Coup fracassant à la tête",
    "Heavy Armor": "armure lourde",
    "Strike vital points": "Transperce les points vitaux",
    "Strike the vitals": "Transperce les points vitaux",
    "Wield a rapier": "Manier une rapière",
    "See the attacker": "Voir la cible",
    "Parry a melee attack": "Parer une attaque au corps à corps",
    "Reducing damage": "Réduisant les dégâts subis",
    "Reducing damage taken": "Réduisant les dégâts subis",
    "Slashing motion": "Attaque tranchante",
    "Riposte": "Riposte",
    "Visceral Thrust": "Frappe vitale",
    "Duelist's Reflex": "Réflexe du duelliste",
    "Do 2d4 additional damage": "Inflige 2d4 de dégâts supplémentaires",
    "Causes bleeding for 6 turns": "Provoque une hémorragie pendant 6 tours",
    "Attempt to parry a melee attack": "Parer une attaque au corps à corps",
    "Does additional 2d4 damage; can inflict Bleeding for 6 turns": "Inflige 2d4 de dégâts supplémentaires, pouvant causer une hémorragie pendant 6 tours",
    "Wield a rapier and see the attacker": "Nécessite de manier une rapière et de voir la cible",
    "Doing 2d4 additional damage and causing bleeding for 6 turns": "Infligeant 2d4 de dégâts perforants supplémentaires et causant une hémorragie pendant 6 tours",
    "Frappez les vitaux, faisant des dégâts supplémentaires 2d4 et causant une hémorragie pendant 6 tours": "Transperce les points vitaux, infligeant 2d4 de dégâts perforants supplémentaires et causant une hémorragie pendant 6 tours",
    "Do 2d4; may cause bleeding for 6 turns": "Inflige 2d4 de dégâts supplémentaires, pouvant causer une hémorragie pendant 6 tours",

    # Nouveaux termes pour BetterCrossbows
    "Superior Piercing": "Perforation supérieure",
    "Mechanical Precision": "Précision mécanique",
    "Loaded Bolt": "Carreau chargé",
    "Load Bolt": "Charger carreau",
    "bolt": "carreau",
    "crossbow": "arbalète",
    
    # Nouveaux termes pour BetterElves
    "Woodland Heritage": "Patrimoine sylvestre",
    "Nature Checks": "tests de Nature",
    "Arcane Ancestry": "Ancêtres des Arcanes",
    "Arcana checks": "tests d'Arcane",
    
    # Nouveaux termes pour BetterGreataxes
    "Break Formation": "Briser la formation",
    "Great Strike": "Grande frappe",
    "Destroy Shield": "Détruire le bouclier",
    "wide arc": "grand arc de cercle",
    "formation": "formation",
    "bleeding": "hémorragie",
    "balance loss": "perte d'équilibre",
    
    # Corrections d'accords
    "1 damage": "1 point de dégât",
    "2 damage": "2 points de dégâts",
    "additional damage": "dégâts supplémentaires",

    # ... termes existants ...
    "bonus action": "action bonus",
    "heavy armor": "armure lourde",
    "medium armor": "armure intermédiaire",
    "nature checks": "tests de Nature",
    "arcana checks": "tests d'Arcanes",
    "frightened": "effrayé",
    "bleeding": "saignement",

     # Nouveaux termes
    "action bonus": "action bonus",
    "armure lourde": "armure lourde",
    "armure intermédiaire": "armure intermédiaire",
    "tests de Nature": "tests de Nature",
    "tests d'Arcanes": "tests d'Arcanes",
    "Carreau chargé": "Carreau chargé",
    "Arbalète déchargée": "Arbalète déchargée",
    "Charger un carreau": "Charger un carreau",
    "Grande frappe": "Grande frappe",
    "Briser la formation": "Briser la formation",
    "Détruire le bouclier": "Détruire le bouclier",
    "Patrimoine sylvestre": "Patrimône sylvestre",
    "Ancêtres des Arcanes": "Ancêtres des Arcanes",
    
    # Corrections de termes
    "Point d'Action": "action",
    "bonus d'Action": "action bonus",
    "Peur": "état effrayé",
    "hémorragie": "saignement",
    "Superior Piercing": "Perforant supérieur",
    "Mechanical Precision": "Précision mécanique",
    "Volley": "Volée",
    "Woodland Heritage": "Patrimoine sylvestre",
    "Arcane Ancestry": "Ancêtres des Arcanes",
    "Break Formation": "Briser la formation",
    "Great Strike": "Grande frappe",
    "against heavy armor": "contre les porteurs d'armure lourde",
    "against medium armor": "contre les porteurs d'armure intermédiaire",

    # Corrections terminologiques BG3
    "Silenced": "Silencieux",  # au lieu de "rendre muet"
    "Disarmed": "Désarmé",
    "See Invisibility": "Voir l'invisibilité",
    "movement points": "mètres de déplacement",
    "points of movement": "mètres de déplacement",
    "attack rolls": "jets d'attaque",
    "damage rolls": "jets de dégâts",
    "per combat": "par combat",
    "once per combat": "1 fois par combat",
    "against target": "contre la cible désignée",
    "against all other targets": "contre toutes les autres cibles",
    "hook strike": "frappe au grappin",
    "spike strike": "frappe perforante",
    "rapid fire": "tir rapide",
    "swift shot": "tir rapide",
    "titan string": "corde de titan",
    "max string": "corde tendue",

    # Corrections finales terminologie BG3
    "Frightened": "Terrifié",  # pas "effrayé"
    "Fear": "Terrifié",  # pas "peur"
    "Silenced": "Silencieux",
    "movement points": "m de déplacement",
    "proficiency bonus": "modificateur de Maîtrise",
    "You gain": "Le porteur obtient",
    "You lose": "Le porteur perd",
    "Sacrifice": "Le porteur sacrifie",
    "Accept the Challenge": "Défi martial",
    "piercing damage": "dégâts perforants",  # toujours au pluriel
    "Hide": "Se cacher",
    "See Invisibility": "Voir l'invisibilité",
    "Rapid Fire": "Flèches multiples",  # pour éviter les doublons

    # Corrections terminologie finale BG3
    "proficiency bonus": "modificateur de Maîtrise",
    "bonus de compétence": "modificateur de Maîtrise", 
    "Titan string": "Corde de titan",
    "Make two shots": "Effectuer deux tirs",
    "Fire at": "Tirer sur",
    "Shoot at": "Tirer sur",
    "gains immunity to": "obtient l'immunité contre",
    "loses access to": "perd l'accès à",
    "Hide action": "capacité Se cacher",
}

# ===== CORRECTIONS ET FIXES =====
REGEX_FIXES: List[Tuple[str, str]] = [
    (r"\b(\d+)D(\d+)\b", r"\1d\2"),
    (r"\b-(\d+)\s*à\s*CA\b", r"Subit un malus de -\1 à la CA"),
    (r"\+\s*(\d+)\s*au\s*jet\s*d'attaque\b", r"+\1 au jet d'attaque"),
    (r"\bdommages\b", "dégâts"),
    (r"\barmure\s*moyenne\b", "armure intermédiaire"),
    (r"\bsignes vitaux\b", "points vitaux"),
    (r"\bFrappez\b", "frappez"),
    (r"\bSaignements\b", "saignements"),
    (r"for (\d+) turns", r"pendant \1 tours"),
    (r"\bdébuts\b", "dégâts"),
    (r"\barure\b", "armure"),
    (r"\bmilles\b", "mailles"),
    (r"\bcoup d'état\b", "coup"),
    (r"\bessayez de se cogner\b", "tentez une attaque"),
    (r"\bs'être exprimé\b", "voir la cible"),
    (r"\bparier\b", "parer"),
    (r"\bau corps à corps à corps\b", "au corps à corps"),
    (r"\bl'l'intelligence\b", "l'Intelligence"),
    (r"\bla la sagesse\b", "la Sagesse"),
    (r"\bd'état\b", ""),
    (r"\bÀ\b", "à"),
    (r"\bdégats\b", "dégâts"),
    (r"\bpareer\b", "parer"),
    (r"\bl'intelligence\b", "l'Intelligence"),
    (r"\bla sagesse\b", "la Sagesse"),
    (r"\binflige inflige\b", "inflige"),
    (r"\bcuelle\b", "cible"),
    (r"\bdégans\b", "dégâts"),
    (r"\brouleaux de dégâts\b", "jets de dégâts"),
    (r"\bbonus d'action\b", "action bonus"),
    (r"\bsanté\b", "points de vie"),
    (r"\b(\d+)%\s*PV\b", r"\1 % de ses PV"),
    (r"\bfeu à\b", "tirez sur"),
    (r"\bpénalité d'attaquer\b", "pénalité au jet d'attaque"),
    (r"\bbearier\b", "porteur"),
]

COMMON_FIXES: List[Tuple[str, str]] = [
    (r"\bmilles\b", "mailles"),
    (r"\barure\b", "armure"),
    (r"\bpourplore\b", "pour un tour"),
    (r"\btournée\b", "tour"),
    (r"\bca\b", "CA"),
    (r"\ben ne portant pas\b", "ne porte pas"),
    (r"\bFracassant de coup\b", "Écrasement magistral"),
    (r"\bun rapière\b", "une rapière"),
    (r"\bTentative de parer\b", "Tenter de parer"),
    (r"\bRéflexe du duelliste\b", "Réflexe du duelliste"),
    (r"\binflige inflige\b", "inflige"),
    (r"\bdégats\b", "dégâts"),
    (r"\bdegâts subs\.\b", "dégâts subis"),
    (r"\bdégâts subs\b", "dégâts subis"),
    (r"\bMagnifique smash\b", "Écrasement magistral"),
    (r"\bBriseur de plaques\b", "Briseur de plates"),
    (r"\bdégâts armées\b", "dégâts"),
    (r"\ben avant pour\b", "l'avantage contre"),
    (r"\bcrainte\b", "peur"),
    (r"\bau déshonneur\b", "au désarmement"),
    (r"\bpour 1\b", "pendant 1 tour"),
    (r"\bpoints de mouvement\b", "mètres de mouvement"),
    (r"\blier une cuelle\b", "agripper une cible"),
    (r"\bles faisant taire\b", "la rendant muette"),
    (r"\btous les deux de bouger\b", "vous deux de vous déplacer"),
    (r"\bune fois par combat\.\b", "Une fois par combat."),
    (r"\bbouclier bearier\b", "porteur de bouclier"),
    (r"\bpar (\d+)\b", r"de \1"),
    (r"\bvers les jets de dégâts\b", "aux jets de dégâts"),
    (r"\bmodificateur de force\b", "modificateur de Force"),
]

DND_SYNTAX_FIXES: List[Tuple[str, str]] = [
    (r"frappez les vitaux, faisant des dégâts supplémentaires (\d+d\d+) et causant une hémorragie pendant (\d+) tours", r"transperce les points vitaux, infligeant \1 de dégâts perforants supplémentaires et causant une hémorragie pendant \2 tours"),
    (r"frappe les vitaux, infligeant (\d+d\d+) dégâts perforants supplémentaires et provoquant un saignement pendant (\d+) tours", r"transperce les points vitaux, infligeant \1 de dégâts perforants supplémentaires et causant une hémorragie pendant \2 tours"),
    (r"provoquant un saignement", r"causant une hémorragie"),
    (r"frappe les organes vitaux", r"transperce les points vitaux"),
    (r"Fait des dégâts supplémentaires (\d+d\d+); peut causer une hémorragie pendant (\d+) tours", r"Inflige \1 de dégâts supplémentaires, pouvant causer une hémorragie pendant \2 tours"),
    (r"\b[Ff]aire\s+(\d+d\d+)\b", r"Inflige \1"),
    (r"\bInflige\s+inflige\s+(\d+d\d+)\s*de\s*dégâts\s*supplémentaires\b", r"Inflige \1 de dégâts supplémentaires"),
    (r"\b(\d+d\d+)\s+supplémentaires\s+de\s*dégâts\b", r"Inflige \1 de dégâts supplémentaires"),
    (r"-(\d+)\s*À?\s*l'intelligence\s*et\s*à\s*la\s*sagesse\b", r"Subit un malus de -\1 à l'Intelligence et à la Sagesse"),
    (r"-(\d+)\s*À?\s*CA\b", r"Subit un malus de -\1 à la CA"),
    (r"-(\d+)\s*to\s*AC\s*for\s*one\s*turn\b", r"Subit un malus de -\1 à la CA jusqu'à la fin du tour suivant"),
    (r"-(\d+)\s*tour\b", r"Subit un malus de -\1 à la CA jusqu'à la fin du tour suivant"),
    (r"\+\s*(\d+)\s*À?\s*CA\b", r"Bénéficie d'un bonus de +\1 à la CA"),
    (r"pour un tour( une tour)?\b", r"jusqu'à la fin de son prochain tour"),
    (r"pour\s+(\d+)\s*tours\b", r"pendant \1 tours"),
    (r"contre (armure (légère|intermédiaire|lourde))", r"contre les porteurs d'armures \2"),
    (r"porteurs d'armures intermédiaire", r"porteurs d'armures intermédiaires"),
    (r"\bdégats\b", r"dégâts"),
    (r"\breducing damage taken\b", r"réduisant les dégâts subis"),
    (r"\breducing damage\b", r"réduisant les dégâts subis"),
    (r"\bAttempt to parry a melee attack\b", r"Parer une attaque au corps à corps"),
    (r"\bUtilisez une motion de tranchage\b", r"Effectue une attaque tranchante"),
    (r"\bpeut infliger des saignements\b", r"peut causer une hémorragie"),
    (r"\bFroissemont\b", r"Riposte"),
    (r"\btentez une attaque la tête\b", r"tentez une attaque à la tête"),
    (r"\bde les commotionner\b", r"l'étourdissant jusqu'à la fin du tour suivant"),
    (r"\binfligeant des saignements\b", r"causant une hémorragie"),
    (r"\bFait (\d+d\d+)\b", r"Inflige \1 de dégâts supplémentaires"),
    (r"\bfrappez-la dur, essayant de le faire saigner\b", r"frappez fort, tentant de provoquer une hémorragie"),
    (r"\bfrappez-la dur, tentant de le faire saigner\b", r"frappez fort, tentant de provoquer une hémorragie"),
    (r"\bextra-dégâts supplémentaires\b", r"dégâts supplémentaires"),
    (r"\bcontre tout ce qui est en pierre, gelé ou petrifié\b", r"contre les cibles pétrifiées, gelées ou de pierre"),
    (r"\bcoup de pouce (\d+d\d+)\b", r"bonus de +\1"),
    (r"\bétourdi\b", r"étourdie"),
    (r"\bdégâts armées\b", r"dégâts"),
    (r"\bperforants décroissants\b", r"dégâts perforants"),
    (r"\bignore une résistance perçante\b", r"ignorant la résistance aux dégâts perforants"),
    (r"\bfaisant (\d+) dégâts supplémentaires\b", r"infligeant \1 dégâts contondants supplémentaires"),
    (r"\bDonne un (\d+d\d+) dégâts supplémentaires\b", r"Inflige \1 de dégâts supplémentaires"),
    (r"\bEssayez d'étourdir\b", r"Tentez d'étourdir"),
    (r"\bsupplémentaires dégâts\b", r"de dégâts supplémentaires"),
    (r"\bLes nains de colline\b", r"Les nains des collines"),
    (r"\bpour attaquer lorsque vous utilisez cette arme\b", r"aux jets d'attaque avec cette arme"),
    (r"\butilisez le dos de votre marteau pour traiter la moitié de vos dégâts armées comme des dégâts perforants, ignorant la résistance aux dégâts perforants\b", r"utilisez le dos de votre marteau pour convertir la moitié de vos dégâts en dégâts perforants, ignorant la résistance aux dégâts perforants"),
    (r"\b\. ignorant\b", r", ignorant"),
    (r"\bChoisir la gale\b", r"Entaille infectée"),
    (r"\bcontre l'armure lourde\b", r"contre les porteurs d'armures lourdes"),
    (r"\ble faire saigner pendant (\d+) tours\b", r"provoquer une hémorragie pendant \1 tours"),
    (r"\bfaites deux coups pour un bonus d'action et d'action\b", r"effectuez deux attaques en dépensant une action bonus et une action"),
    (r"\b1,5 fois votre modificateur\b", r"1,5 fois votre modificateur"),
    (r"\butilisez le crochet sur votre hache pour vous lier une cuelle pendant (\d+) tours\b", r"utilisez le crochet de votre hache pour agripper une cible pendant \1 tours"),
    (r"\bsacrifiez (\d+)% de votre santé\b", r"sacrifiez \1 % de vos points de vie"),
    (r"\bgagner immunité\b", r"gagner une immunité"),
    (r"\bMaîtrise dans les arcanes\b", r"Maîtrise en Arcanes"),
    (r"\bavantage sur les contrôles\b", r"avantage aux tests"),
    (r"\bdes arcanes\b", r"d’Arcanes"),
    (r"\bMaîtrise dans les arcanes;\b", r"Maîtrise dans les Arcanes,"),

    # Corrections pour la cohérence BG3
    (r'\beffrayé\b', 'Terrifié'),
    (r'\bà l\'état effrayé\b', 'contre l\'état Terrifié'),
    (r'\bcontre l\'état désarmé\b', 'contre l\'état Désarmé'),
    (r'\bVous (.+)\b', r'Le porteur \1'),  # Conversion 2e vers 3e personne
    (r'\bvos points de vie\b', 'ses points de vie maximum'),
    (r'\bvotre (.+)\b', r'son \1'),  # Conversion possessifs

    # Cohérence de personne pour BG3
    (r'\bVous (.+?ez)\b', r'Le porteur \1'),  # Vous obtenez -> Le porteur obtient
    (r'\bSacrifiez\b', 'Le porteur sacrifie'),
    (r'\bGagnez\b', 'Le porteur gagne'),
    (r'\bPerdez\b', 'Le porteur perd'),
    (r'\bvotre (.+?)\b', r'son \1'),  # vos -> ses
    (r'\bvos (.+?)\b', r'ses \1'),   # vos -> ses

]

ACRONYMS = {"CA", "AC", "HP", "DND", "DPS", "DD", "JS", "JA", "TC", "PV"}
DICE_PATTERN = re.compile(r"\b\d+[dD]\d+(?:[+-]\d+)?\b")