#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_bg3_translator.py - Script de configuration initiale
Crée la structure de dossiers et vérifie les dépendances
"""

import os
import sys
from pathlib import Path
import json
import subprocess

def create_directory_structure():
    """Crée la structure de dossiers nécessaire"""
    directories = [
        "config",
        "config/mods", 
        "data",
        "cache",
        "logs",
        "temp",
        "output",
        "input",
        "backups"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Dossier créé: {directory}")

def check_dependencies():
    """Vérifie les dépendances Python"""
    required_packages = [
        "deepl",
        "requests", 
        "chardet",
        "python-dotenv"
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"✗ {package} - MANQUANT")
    
    if missing:
        print(f"\nPour installer les dépendances manquantes:")
        print(f"pip install {' '.join(missing)}")
        return False
    return True

def create_env_template():
    """Crée un template .env si absent"""
    env_file = Path(".env")
    if not env_file.exists():
        env_content = """# BG3 Translator - Configuration des clés API
DEEPL_API_KEY=your_deepl_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Chemins optionnels
# DIVINE_EXE_PATH=/path/to/divine.exe
# CONFIG_DIR=./config
# OUTPUT_DIR=./output
"""
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("✓ Fichier .env template créé")
    else:
        print("✓ Fichier .env existe déjà")

def validate_configuration():
    """Valide les fichiers de configuration"""
    config_files = [
        "config/bg3_translator_config.json",
        "config/bg3_translation_rules.json"
    ]
    
    all_valid = True
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✓ {config_file}")
            except json.JSONDecodeError as e:
                print(f"✗ {config_file} - ERREUR JSON: {e}")
                all_valid = False
        else:
            print(f"✗ {config_file} - MANQUANT")
            all_valid = False
    
    return all_valid

def main():
    print("=== Configuration BG3 Translator v2.0 ===\n")
    
    # 1. Structure des dossiers
    print("1. Création de la structure de dossiers...")
    create_directory_structure()
    print()
    
    # 2. Vérification des dépendances
    print("2. Vérification des dépendances Python...")
    deps_ok = check_dependencies()
    print()
    
    # 3. Configuration de l'environnement
    print("3. Configuration de l'environnement...")
    create_env_template()
    print()
    
    # 4. Validation des configurations
    print("4. Validation des fichiers de configuration...")
    config_ok = validate_configuration()
    print()
    
    # Rapport final
    print("=== RAPPORT DE CONFIGURATION ===")
    if deps_ok and config_ok:
        print("✅ Configuration réussie! Le traducteur est prêt.")
        print("\nProchaines étapes:")
        print("1. Éditez le fichier .env avec vos clés API")
        print("2. Placez divine.exe dans le dossier tools/")
        print("3. Testez avec: python bg3_translator_core.py --help")
    else:
        print("❌ Configuration incomplète. Résolvez les erreurs ci-dessus.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

---

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_mod.py - Script de traduction simplifié
Usage rapide pour traduire un mod
"""

import sys
import argparse
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def main():
    parser = argparse.ArgumentParser(
        description="BG3 Mod Translator - Script de traduction simplifié"
    )
    
    # Arguments requis
    parser.add_argument("mod_file", help="Fichier ZIP du mod à traduire")
    parser.add_argument("--author", required=True, help="Nom de l'auteur de la traduction")
    
    # Arguments optionnels avec valeurs par défaut
    parser.add_argument("--divine", default="tools/divine.exe", help="Chemin vers divine.exe")
    parser.add_argument("--output", default="output/", help="Dossier de sortie")
    parser.add_argument("--config", default="config/bg3_translator_config.json", help="Fichier de configuration")
    
    # Options
    parser.add_argument("--use-llm", action="store_true", help="Active l'optimisation LLM")
    parser.add_argument("--emit-loca", action="store_true", help="Génère les fichiers LOCA")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans modification")
    
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Chargement des variables d'environnement
    load_dotenv()
    
    deepl_key = os.getenv('DEEPL_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    if not deepl_key:
        logger.error("DEEPL_API_KEY manquant dans le fichier .env")
        return 1
    
    if args.use_llm and not openrouter_key:
        logger.warning("OPENROUTER_API_KEY manquant - LLM désactivé")
        args.use_llm = False
    
    try:
        # Import dynamique pour éviter les erreurs si les modules ne sont pas trouvés
        from bg3_translator_integration import EnhancedBG3Translator
        from bg3_translator_core import TranslationConfig, load_configuration
        
        # Configuration
        base_config = load_configuration(Path(args.config))
        base_config.use_llm_optimization = args.use_llm
        base_config.emit_loca_files = args.emit_loca
        
        # Initialisation du traducteur
        translator = EnhancedBG3Translator(
            config=base_config,
            divine_path=Path(args.divine),
            deepl_key=deepl_key,
            main_config_path=Path(args.config)
        )
        
        if args.dry_run:
            logger.info("Mode simulation - Aucune modification ne sera effectuée")
            return 0
        
        # Traduction
        logger.info(f"Démarrage de la traduction: {args.mod_file}")
        
        result = translator.translate_mod(
            mod_zip=Path(args.mod_file),
            output_path=Path(args.output),
            translation_author=args.author,
            openrouter_key=openrouter_key if args.use_llm else None
        )
        
        # Résultats
        if result.success:
            logger.info(f"✅ Traduction réussie: {result.message}")
            
            # Statistiques
            stats = translator.get_comprehensive_stats()
            logger.info(f"Cache: {stats['translation']['cache_stats']}")
            logger.info(f"Apprentissage: {stats['learning']['learned_rules']} règles apprises")
            
            return 0
        else:
            logger.error(f"❌ Traduction échouée: {result.message}")
            return 1
            
    except ImportError as e:
        logger.error(f"Module manquant: {e}")
        logger.error("Exécutez d'abord: python setup_bg3_translator.py")
        return 1
    except Exception as e:
        logger.error(f"Erreur: {e}")
        if args.verbose:
            import traceback
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit(main())