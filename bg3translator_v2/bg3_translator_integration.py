#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BG3 Translator - Exemple d'intégration avec la nouvelle architecture
Démontre comment utiliser le système modulaire avec auto-amélioration
"""

from pathlib import Path
from bg3_translator_core import BG3ModTranslator, TranslationConfig, load_configuration
from dynamic_rules_manager import DynamicRulesManager
import json
import logging

logger = logging.getLogger(__name__)

class EnhancedBG3Translator(BG3ModTranslator):
    """Version améliorée du traducteur avec système d'apprentissage"""
    
    def __init__(self, config: TranslationConfig, divine_path: Path, deepl_key: str,
                 main_config_path: Path, glossary_manager=None):
        
        # Charger la configuration principale
        with open(main_config_path, 'r', encoding='utf-8') as f:
            self.main_config = json.load(f)
        
        # Initialiser le gestionnaire de règles dynamiques
        base_rules_path = Path(self.main_config["rules_configuration"]["base_rules_file"])
        learned_rules_path = Path(self.main_config["rules_configuration"]["learned_rules_file"])
        
        self.dynamic_rules = DynamicRulesManager(base_rules_path, learned_rules_path)
        
        # Configurer l'apprentissage automatique
        learning_config = self.main_config["rules_configuration"]["auto_learning"]
        self.dynamic_rules.learning_config.update(learning_config)
        
        # Remplacer le moteur de règles par défaut
        super().__init__(config, divine_path, deepl_key, None, glossary_manager)
        self.rule_engine = self.dynamic_rules
        
        # Réinitialiser le traducteur avec le nouveau moteur
        from bg3_translator_core import DeepLTranslator
        self.translator = DeepLTranslator(
            deepl_key, config, self.dynamic_rules, glossary_manager
        )
        
        logger.info("Traducteur amélioré initialisé avec système d'apprentissage")
    
    def translate_mod(self, mod_zip: Path, output_path: Path, translation_author: str,
                     mod_suffix: str = "_FR", openrouter_key: str = None) -> dict:
        """Version améliorée de la traduction avec détection automatique du mod"""
        
        # Détecter le type de mod pour charger les règles spécifiques
        detected_mod = self._detect_mod_type(mod_zip)
        if detected_mod:
            self._load_mod_specific_rules(detected_mod)
        
        # Appeler la traduction de base
        result = super().translate_mod(mod_zip, output_path, translation_author, mod_suffix, openrouter_key)
        
        # Évaluer et sauvegarder les améliorations apprises
        if self.dynamic_rules.learning_config["enabled"]:
            self.dynamic_rules._evaluate_learning_candidates()
            self.dynamic_rules.save_learned_rules()
        
        # Ajouter les statistiques d'apprentissage au résultat
        if result.success:
            learning_stats = self.dynamic_rules.get_learning_statistics()
            result.data = result.data or {}
            result.data["learning_statistics"] = learning_stats
        
        return result
    
    def _detect_mod_type(self, mod_zip: Path) -> str:
        """Détecte automatiquement le type de mod basé sur son nom et contenu"""
        mod_name = mod_zip.stem.lower()
        
        known_mods = self.main_config["mod_detection"]["known_mods"]
        
        # Détection par nom de fichier
        for mod_key, mod_info in known_mods.items():
            if mod_key.lower() in mod_name:
                logger.info(f"Mod détecté par nom: {mod_key}")
                return mod_key
        
        # TODO: Détection par analyse du contenu si nécessaire
        # Cette fonctionnalité pourrait analyser les fichiers XML pour détecter
        # des patterns spécifiques à certains mods
        
        return None
    
    def _load_mod_specific_rules(self, mod_name: str) -> None:
        """Charge les règles spécifiques au mod détecté"""
        known_mods = self.main_config["mod_detection"]["known_mods"]
        
        if mod_name in known_mods:
            mod_config = known_mods[mod_name]
            rules_file = Path(mod_config["rules_file"])
            
            if rules_file.exists():
                success = self.dynamic_rules.load_mod_specific_rules(mod_name, rules_file)
                if success:
                    logger.info(f"Règles spécifiques chargées pour {mod_name}")
                else:
                    logger.warning(f"Échec du chargement des règles pour {mod_name}")
            else:
                logger.warning(f"Fichier de règles introuvable: {rules_file}")
    
    def export_learning_review(self, output_path: Path) -> bool:
        """Exporte les règles apprises pour révision humaine"""
        return self.dynamic_rules.export_rules_for_review(output_path)
    
    def import_reviewed_rules(self, reviewed_path: Path) -> int:
        """Importe les règles révisées par un humain"""
        return self.dynamic_rules.import_reviewed_rules(reviewed_path)
    
    def get_comprehensive_stats(self) -> dict:
        """Retourne des statistiques complètes du système"""
        base_stats = super().get_translation_stats()
        learning_stats = self.dynamic_rules.get_learning_statistics()
        
        return {
            "translation": base_stats,
            "learning": learning_stats,
            "configuration": {
                "auto_learning": self.dynamic_rules.learning_config["enabled"],
                "auto_improve": self.dynamic_rules.learning_config["auto_improve"],
                "confidence_threshold": self.dynamic_rules.learning_config["confidence_threshold"]
            }
        }

def main_enhanced():
    """Exemple d'utilisation du traducteur amélioré"""
    
    # Configuration des chemins
    config_path = Path("config/bg3_translator_config.json")
    mod_zip = Path("input/BetterCrossbows.zip")
    divine_exe = Path("tools/divine.exe")
    output_dir = Path("output/")
    
    # Clés API (à charger depuis l'environnement)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    deepl_key = os.getenv('DEEPL_API_KEY')
    openrouter_key = os.getenv('OPENROUTER_API_KEY')
    
    try:
        # Chargement de la configuration
        base_config = load_configuration()
        base_config.use_llm_optimization = True
        
        # Initialisation du glossaire (optionnel)
        glossary_manager = None
        try:
            from glossary_manager import GlossaryManager
            glossary_manager = GlossaryManager()
        except ImportError:
            logger.warning("Gestionnaire de glossaire non disponible")
        
        # Initialisation du traducteur amélioré
        translator = EnhancedBG3Translator(
            config=base_config,
            divine_path=divine_exe,
            deepl_key=deepl_key,
            main_config_path=config_path,
            glossary_manager=glossary_manager
        )
        
        # Traduction du mod
        logger.info(f"Démarrage de la traduction: {mod_zip}")
        
        result = translator.translate_mod(
            mod_zip=mod_zip,
            output_path=output_dir,
            translation_author="Mon Nom",
            openrouter_key=openrouter_key
        )
        
        # Rapport des résultats
        if result.success:
            logger.info(f"✅ Traduction réussie: {result.message}")
            
            # Affichage des statistiques complètes
            stats = translator.get_comprehensive_stats()
            logger.info("📊 Statistiques de traduction:")
            logger.info(f"  - Cache: {stats['translation']['cache_stats']}")
            logger.info(f"  - Apprentissage: {stats['learning']}")
            
            # Export pour révision humaine (optionnel)
            review_path = output_dir / "learned_rules_review.json"
            if translator.export_learning_review(review_path):
                logger.info(f"📋 Règles exportées pour révision: {review_path}")
            
            return 0
        else:
            logger.error(f"❌ Traduction échouée: {result.message}")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1

def workflow_with_human_review():
    """Exemple de workflow avec révision humaine des règles apprises"""
    
    # Étape 1: Traduction avec apprentissage
    logger.info("=== ÉTAPE 1: Traduction avec apprentissage ===")
    exit_code = main_enhanced()
    
    if exit_code != 0:
        return exit_code
    
    # Étape 2: Révision humaine (simulation)
    logger.info("=== ÉTAPE 2: Révision humaine des règles apprises ===")
    review_file = Path("output/learned_rules_review.json")
    
    if review_file.exists():
        # Simulation d'une révision humaine (en pratique, un humain éditerait ce fichier)
        with open(review_file, 'r', encoding='utf-8') as f:
            review_data = json.load(f)
        
        # Auto-approuver les règles avec haute confiance (exemple)
        for rule in review_data.get("rules_for_review", []):
            if rule.get("confidence", 0) > 0.9:
                rule["approved"] = True
                rule["review_notes"] = "Auto-approuvée (haute confiance)"
            elif rule.get("confidence", 0) < 0.6:
                rule["approved"] = False
                rule["review_notes"] = "Rejetée (faible confiance)"
            else:
                rule["approved"] = None  # Nécessite révision manuelle
                rule["review_notes"] = "Révision manuelle requise"
        
        # Sauvegarder les révisions
        with open(review_file, 'w', encoding='utf-8') as f:
            json.dump(review_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📝 Révision simulée sauvegardée: {review_file}")
    
    # Étape 3: Import des règles révisées
    logger.info("=== ÉTAPE 3: Import des règles révisées ===")
    
    # Réinitialiser le traducteur pour importer les révisions
    config_path = Path("config/bg3_translator_config.json")
    base_config = load_configuration()
    
    translator = EnhancedBG3Translator(
        config=base_config,
        divine_path=Path("tools/divine.exe"),
        deepl_key=os.getenv('DEEPL_API_KEY'),
        main_config_path=config_path
    )
    
    approved_count = translator.import_reviewed_rules(review_file)
    logger.info(f"✅ {approved_count} règles approuvées importées")
    
    return 0

if __name__ == "__main__":
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Choix du workflow
    import sys
    
    if "--review-workflow" in sys.argv:
        exit(workflow_with_human_review())
    else:
        exit(main_enhanced())