#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
translate_mod.py - Script de traduction simplifié
Usage rapide pour traduire un mod BG3
"""

import sys
import argparse
from pathlib import Path
import os
from dotenv import load_dotenv
import logging

def setup_logging(verbose=False):
    """Configure le système de logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def check_prerequisites(args):
    """Vérifie que tous les prérequis sont présents"""
    logger = logging.getLogger(__name__)
    errors = []
    
    # Vérifier le fichier mod
    if not Path(args.mod_file).exists():
        errors.append(f"Fichier mod introuvable: {args.mod_file}")
    
    # Vérifier divine.exe
    if not Path(args.divine).exists():
        errors.append(f"Divine.exe introuvable: {args.divine}")
    
    # Vérifier les clés API
    if not os.getenv('DEEPL_API_KEY'):
        errors.append("DEEPL_API_KEY manquant dans le fichier .env")
    
    if args.use_llm and not os.getenv('OPENROUTER_API_KEY'):
        logger.warning("OPENROUTER_API_KEY manquant - LLM désactivé")
        args.use_llm = False
    
    # Vérifier les fichiers de configuration (optionnels)
    if not Path(args.config).exists():
        logger.warning(f"Fichier de configuration manquant: {args.config}")
        logger.warning("Utilisation de la configuration par défaut")
    
    return errors

def main():
    parser = argparse.ArgumentParser(
        description="BG3 Mod Translator - Script de traduction simplifié",
        epilog="""
Exemples:
  python translate_mod.py MonMod.zip --author "Votre Nom"
  python translate_mod.py MonMod.zip --author "Votre Nom" --use-llm
  python translate_mod.py MonMod.zip --author "Votre Nom" --dry-run
        """
    )
    
    # Arguments requis
    parser.add_argument("mod_file", help="Fichier ZIP du mod à traduire")
    parser.add_argument("--author", required=True, help="Nom de l'auteur de la traduction")
    
    # Arguments optionnels avec valeurs par défaut
    parser.add_argument("--divine", default="tools/divine.exe", 
                       help="Chemin vers divine.exe (défaut: tools/divine.exe)")
    parser.add_argument("--output", default="output/", 
                       help="Dossier de sortie (défaut: output/)")
    parser.add_argument("--config", default="config/bg3_translator_config.json", 
                       help="Fichier de configuration (défaut: config/bg3_translator_config.json)")
    parser.add_argument("--suffix", default="_FR",
                       help="Suffixe du mod traduit (défaut: _FR)")
    
    # Options
    parser.add_argument("--use-llm", action="store_true", 
                       help="Active l'optimisation LLM (nécessite OPENROUTER_API_KEY)")
    parser.add_argument("--emit-loca", action="store_true", 
                       help="Génère les fichiers LOCA")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Mode verbeux")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Simulation sans modification")
    parser.add_argument("--clear-cache", action="store_true",
                       help="Vide le cache de traduction")
    
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Chargement des variables d'environnement
    load_dotenv()
    
    # Vérification des prérequis
    errors = check_prerequisites(args)
    if errors:
        logger.error("Erreurs de configuration:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    
    # Récupération des clés API
    deepl_key = os.getenv('DEEPL_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    try:
        # Import des modules avec gestion d'erreur
        try:
            from bg3_translator_integration import EnhancedBG3Translator
            from bg3_translator_core import TranslationConfig, load_configuration
        except ImportError as e:
            logger.error(f"Module manquant: {e}")
            logger.error("Vérifiez que tous les fichiers Python sont présents:")
            logger.error("  - bg3_translator_core.py")
            logger.error("  - bg3_translator_integration.py")
            logger.error("  - dynamic_rules_manager.py")
            return 1
        
        # Configuration avec gestion d'erreur
        try:
            base_config = load_configuration(Path(args.config))
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de la configuration: {e}")
            logger.info("Utilisation de la configuration par défaut")
            base_config = TranslationConfig()
        
        # Application des options CLI
        base_config.use_llm_optimization = args.use_llm
        base_config.emit_loca_files = args.emit_loca
        base_config.clear_cache = args.clear_cache
        
        # Initialisation du glossaire (optionnel)
        glossary_manager = None
        try:
            from glossary_manager import GlossaryManager
            glossary_manager = GlossaryManager()
            logger.info("Gestionnaire de glossaire chargé")
        except ImportError:
            logger.warning("Gestionnaire de glossaire non disponible - fonctionnalité de base uniquement")
        except Exception as e:
            logger.warning(f"Erreur lors du chargement du glossaire: {e}")
        
        # Initialisation du traducteur
        logger.info("Initialisation du traducteur...")
        try:
            translator = EnhancedBG3Translator(
                config=base_config,
                divine_path=Path(args.divine),
                deepl_key=deepl_key,
                main_config_path=Path(args.config) if Path(args.config).exists() else None,
                glossary_manager=glossary_manager
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du traducteur: {e}")
            return 1
        
        # Mode simulation
        if args.dry_run:
            logger.info("=== MODE SIMULATION ===")
            logger.info("Aucune modification ne sera effectuée")
            logger.info(f"Fichier source: {args.mod_file}")
            logger.info(f"Auteur: {args.author}")
            logger.info(f"Sortie: {args.output}")
            logger.info(f"LLM activé: {args.use_llm}")
            logger.info(f"Génération LOCA: {args.emit_loca}")
            logger.info("Simulation terminée avec succès")
            return 0
        
        # Traduction réelle
        logger.info("=== DÉBUT DE LA TRADUCTION ===")
        logger.info(f"Fichier source: {args.mod_file}")
        logger.info(f"Auteur: {args.author}")
        logger.info(f"LLM: {'Activé' if args.use_llm else 'Désactivé'}")
        
        result = translator.translate_mod(
            mod_zip=Path(args.mod_file),
            output_path=Path(args.output),
            translation_author=args.author,
            mod_suffix=args.suffix,
            openrouter_key=openrouter_key if args.use_llm else None
        )
        
        # Rapport des résultats
        if result.success:
            logger.info("=== TRADUCTION RÉUSSIE ===")
            logger.info(f"Message: {result.message}")
            
            # Affichage des statistiques si disponibles
            try:
                stats = translator.get_comprehensive_stats()
                logger.info("=== STATISTIQUES ===")
                
                # Stats de cache
                cache_stats = stats.get('translation', {}).get('cache_stats', {})
                if cache_stats:
                    logger.info(f"Cache - Hits: {cache_stats.get('hits', 0)}, Misses: {cache_stats.get('misses', 0)}")
                
                # Stats d'apprentissage
                learning_stats = stats.get('learning', {})
                if learning_stats:
                    learned_rules = learning_stats.get('learned_rules', 0)
                    candidates = learning_stats.get('learning_candidates', 0)
                    logger.info(f"Apprentissage - Règles apprises: {learned_rules}, Candidats: {candidates}")
                
            except Exception as e:
                logger.debug(f"Erreur lors de l'affichage des statistiques: {e}")
            
            # Export des règles apprises pour révision
            try:
                review_path = Path(args.output) / "learned_rules_review.json"
                if translator.export_learning_review(review_path):
                    logger.info(f"Règles exportées pour révision: {review_path}")
            except Exception as e:
                logger.debug(f"Erreur lors de l'export des règles: {e}")
            
            # Localisation des fichiers de sortie
            output_files = list(Path(args.output).glob("*"))
            if output_files:
                logger.info("=== FICHIERS GÉNÉRÉS ===")
                for file in output_files:
                    if file.is_file():
                        logger.info(f"  - {file.name}")
            
            logger.info("Traduction terminée avec succès!")
            return 0
            
        else:
            logger.error("=== TRADUCTION ÉCHOUÉE ===")
            logger.error(f"Message: {result.message}")
            
            if result.errors:
                logger.error("Erreurs détaillées:")
                for error in result.errors:
                    logger.error(f"  - {error}")
            
            return 1
            
    except KeyboardInterrupt:
        logger.info("Traduction interrompue par l'utilisateur")
        return 130
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        if args.verbose:
            import traceback
            logger.debug("Traceback complet:")
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit(main())