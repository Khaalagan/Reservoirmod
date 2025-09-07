#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BG3 Mod Translator - Core Engine
Professional refactored version for maximum modularity and extensibility.
"""

from __future__ import annotations

import os
import re
import json
import shutil
import zipfile
import tempfile
import subprocess
import argparse
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import xml.etree.ElementTree as ET
import requests
import deepl
import chardet
from dotenv import load_dotenv

# Configuration
os.environ["PYTHONIOENCODING"] = "utf-8"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION AND DATA CLASSES
# ============================================================================

@dataclass
class TranslationConfig:
    """Configuration pour la traduction"""
    source_lang: str = "EN"
    target_lang: str = "FR"
    use_llm_optimization: bool = False
    emit_loca_files: bool = False
    clear_cache: bool = False
    parallel_translation: bool = True
    max_workers: int = 4

@dataclass
class ModMetadata:
    """Métadonnées d'un mod"""
    name: str
    author: str
    uuid: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_info_json(cls, info_path: Path) -> 'ModMetadata':
        """Crée une instance depuis un fichier info.json"""
        with open(info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            name=data.get("Name", ""),
            author=data.get("Author", "Unknown"),
            uuid=data.get("UUID", str(uuid.uuid4())),
            description=data.get("Description", "")
        )

@dataclass
class ProcessingResult:
    """Résultat d'une opération de traitement"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)

# ============================================================================
# ABSTRACT INTERFACES
# ============================================================================

class ITranslationProcessor(ABC):
    """Interface pour les processeurs de traduction"""
    
    @abstractmethod
    def process_text(self, text: str, context: Dict[str, Any] = None) -> str:
        """Traite un texte selon les règles spécifiques"""
        pass

class IFileHandler(ABC):
    """Interface pour la gestion des fichiers"""
    
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Vérifie si ce handler peut traiter le fichier"""
        pass
    
    @abstractmethod
    def process_file(self, file_path: Path, processor: ITranslationProcessor) -> ProcessingResult:
        """Traite un fichier spécifique"""
        pass

class IRuleEngine(ABC):
    """Interface pour les moteurs de règles"""
    
    @abstractmethod
    def load_rules(self, rules_path: Path) -> bool:
        """Charge les règles depuis un fichier"""
        pass
    
    @abstractmethod
    def apply_rules(self, text: str, stage: str) -> str:
        """Applique les règles à un stade donné"""
        pass

# ============================================================================
# CORE COMPONENTS
# ============================================================================

class TextProcessor:
    """Processeur de texte avec fonctionnalités de base"""
    
    # Patterns statiques pour les expressions communes
    DICE_PATTERN = re.compile(r"\b(\d+d\d+(?:\s*[+-]\s*\d+)?)\b", re.IGNORECASE)
    ENCODING_FIXES = {
        "â€™": "'", "â€œ": '"', "â€": '"', 
        "Ã©": "é", "Ã ": "à", "Ã§": "ç", "Ã¨": "è", "Ã´": "ô"
    }
    
    def __init__(self):
        self._protected_expressions = {}
    
    def clean_encoding(self, text: str) -> str:
        """Corrige les problèmes d'encodage"""
        if not text:
            return text
        
        result = text
        for bad, good in self.ENCODING_FIXES.items():
            result = result.replace(bad, good)
        return result
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalise les espaces"""
        return re.sub(r"\s+", " ", text).strip() if text else text
    
    def protect_expressions(self, text: str, patterns: List[re.Pattern]) -> Tuple[str, Dict[str, str]]:
        """Protège certaines expressions pendant le traitement"""
        protected_text = text
        protections = {}
        
        for i, pattern in enumerate(patterns):
            matches = pattern.findall(text)
            for j, match in enumerate(matches):
                placeholder = f"__PROTECTED_{i}_{j}__"
                protections[placeholder] = match
                protected_text = protected_text.replace(match, placeholder)
        
        return protected_text, protections
    
    def restore_expressions(self, text: str, protections: Dict[str, str]) -> str:
        """Restaure les expressions protégées"""
        result = text
        for placeholder, original in protections.items():
            result = result.replace(placeholder, original)
        return result

class TranslationCache:
    """Cache de traduction thread-safe"""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._stats = {"hits": 0, "misses": 0}
    
    def get(self, key: str) -> Optional[str]:
        """Récupère une traduction du cache"""
        if key in self._cache:
            self._stats["hits"] += 1
            return self._cache[key]
        self._stats["misses"] += 1
        return None
    
    def set(self, key: str, value: str) -> None:
        """Stocke une traduction dans le cache"""
        self._cache[key] = value
    
    def clear(self) -> None:
        """Vide le cache"""
        self._cache.clear()
        self._stats = {"hits": 0, "misses": 0}
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques du cache"""
        return self._stats.copy()

class RuleEngine(IRuleEngine):
    """Moteur de règles configurable"""
    
    def __init__(self):
        self._rules: Dict[str, List[Tuple[str, str]]] = {
            "pre_translation": [],
            "post_translation": [],
            "final_cleanup": []
        }
    
    def load_rules(self, rules_path: Path) -> bool:
        """Charge les règles depuis un fichier JSON"""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            for stage, rules in rules_data.items():
                if stage in self._rules:
                    self._rules[stage] = [(rule["pattern"], rule["replacement"]) 
                                        for rule in rules]
            
            logger.info(f"Règles chargées depuis {rules_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des règles: {e}")
            return False
    
    def apply_rules(self, text: str, stage: str) -> str:
        """Applique les règles d'un stade donné"""
        if not text or stage not in self._rules:
            return text
        
        result = text
        for pattern, replacement in self._rules[stage]:
            try:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            except re.error as e:
                logger.warning(f"Erreur regex '{pattern}': {e}")
        
        return result
    
    def add_rule(self, stage: str, pattern: str, replacement: str) -> None:
        """Ajoute une règle dynamiquement"""
        if stage not in self._rules:
            self._rules[stage] = []
        self._rules[stage].append((pattern, replacement))

class DeepLTranslator(ITranslationProcessor):
    """Processeur de traduction utilisant DeepL"""
    
    def __init__(self, api_key: str, config: TranslationConfig, 
                 rule_engine: RuleEngine, glossary_manager=None):
        self.translator = deepl.Translator(auth_key=api_key)
        self.config = config
        self.rule_engine = rule_engine
        self.glossary_manager = glossary_manager
        self.text_processor = TextProcessor()
        self.cache = TranslationCache()
    
    def process_text(self, text: str, context: Dict[str, Any] = None) -> str:
        """Traite et traduit un texte"""
        if not text or not text.strip():
            return text
        
        # Nettoyage initial
        cleaned = self.text_processor.clean_encoding(text)
        cleaned = self.text_processor.normalize_whitespace(cleaned)
        
        # Vérification du cache
        cache_key = f"{cleaned}_{self.config.use_llm_optimization}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Protection des expressions sensibles
            protected, protections = self.text_processor.protect_expressions(
                cleaned, [self.text_processor.DICE_PATTERN]
            )
            
            # Pré-traitement
            preprocessed = self.rule_engine.apply_rules(protected, "pre_translation")
            
            # Application du glossaire
            if self.glossary_manager:
                preprocessed = self._apply_glossary(preprocessed)
            
            # Traduction DeepL
            result = self.translator.translate_text(
                preprocessed, 
                source_lang=self.config.source_lang,
                target_lang=self.config.target_lang
            )
            translated = result.text
            
            # Post-traitement
            translated = self.rule_engine.apply_rules(translated, "post_translation")
            
            # Optimisation LLM si activée
            if self.config.use_llm_optimization and context and context.get("openrouter_key"):
                translated = self._optimize_with_llm(cleaned, translated, context["openrouter_key"])
            
            # Nettoyage final
            final_result = self.rule_engine.apply_rules(translated, "final_cleanup")
            final_result = self.text_processor.restore_expressions(final_result, protections)
            
            # Mise en cache
            self.cache.set(cache_key, final_result)
            return final_result
            
        except Exception as e:
            logger.error(f"Erreur de traduction: {e}")
            return text
    
    def _apply_glossary(self, text: str) -> str:
        """Applique les termes du glossaire"""
        if not hasattr(self.glossary_manager, 'get_glossary'):
            return text
        
        glossary = self.glossary_manager.get_glossary()
        result = text
        for term, translation in glossary.items():
            result = re.sub(rf"\b{re.escape(term)}\b", translation, result, flags=re.IGNORECASE)
        
        return result
    
    def _optimize_with_llm(self, source: str, translation: str, api_key: str) -> str:
        """Optimise la traduction avec un LLM"""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Tu es un expert en traduction BG3. Améliore la traduction si nécessaire, en respectant les conventions du jeu."
                        },
                        {
                            "role": "user",
                            "content": f"Source: {source}\nTraduction: {translation}\nAméliore si nécessaire:"
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.ok:
                data = response.json()
                optimized = data["choices"][0]["message"]["content"].strip()
                logger.debug(f"LLM optimization: '{translation}' -> '{optimized}'")
                return optimized
                
        except Exception as e:
            logger.warning(f"Erreur LLM: {e}")
        
        return translation

class XMLFileHandler(IFileHandler):
    """Gestionnaire de fichiers XML"""
    
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.xml'
    
    def process_file(self, file_path: Path, processor: ITranslationProcessor) -> ProcessingResult:
        """Traite un fichier XML"""
        try:
            # Lecture avec détection d'encodage
            with open(file_path, "rb") as f:
                raw = f.read()
                encoding = chardet.detect(raw).get("encoding") or "utf-8"
            
            text = raw.decode(encoding, errors="ignore")
            root = ET.fromstring(text)
            
            # Configuration de la locale française
            if root.tag == "contentList" and not root.get("locale"):
                root.set("locale", "fr-FR")
            
            # Traduction des éléments de contenu
            translated_count = 0
            for elem in root.findall(".//content"):
                if elem.text and elem.text.strip():
                    translated_text = processor.process_text(elem.text)
                    elem.text = translated_text
                    translated_count += 1
            
            if translated_count == 0:
                return ProcessingResult(
                    success=False,
                    message=f"Aucun contenu traduisible trouvé dans {file_path}"
                )
            
            # Sauvegarde
            xml_string = ET.tostring(root, encoding='unicode')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n')
                f.write(xml_string)
            
            return ProcessingResult(
                success=True,
                message=f"Traduction réussie: {translated_count} éléments traduits",
                data={"translated_elements": translated_count}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors du traitement de {file_path}: {e}"
            )

class DivineToolsManager:
    """Gestionnaire des outils Divine pour BG3"""
    
    def __init__(self, divine_path: Path):
        self.divine_path = Path(divine_path).resolve()
        if not self.divine_path.exists():
            raise FileNotFoundError(f"Divine.exe introuvable: {divine_path}")
    
    def extract_pak(self, pak_file: Path, output_dir: Path) -> ProcessingResult:
        """Extrait un fichier PAK"""
        try:
            cmd = [
                str(self.divine_path),
                "-g", "bg3",
                "--action", "extract-package",
                "--source", str(pak_file.resolve()),
                "--destination", str(output_dir.resolve())
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Nettoyage du dossier Public
            public_dir = output_dir / "Public"
            if public_dir.exists():
                shutil.rmtree(public_dir, ignore_errors=True)
            
            return ProcessingResult(
                success=True,
                message=f"Extraction PAK réussie: {pak_file} -> {output_dir}"
            )
            
        except subprocess.CalledProcessError as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur Divine lors de l'extraction: {e}",
                errors=[e.stderr] if e.stderr else []
            )
    
    def create_pak(self, source_dir: Path, output_pak: Path) -> ProcessingResult:
        """Crée un fichier PAK"""
        try:
            cmd = [
                str(self.divine_path),
                "-g", "bg3",
                "--action", "create-package",
                "--source", str(source_dir.resolve()),
                "--destination", str(output_pak.resolve())
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            return ProcessingResult(
                success=True,
                message=f"Création PAK réussie: {source_dir} -> {output_pak}"
            )
            
        except subprocess.CalledProcessError as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur Divine lors de la création: {e}",
                errors=[e.stderr] if e.stderr else []
            )
    
    def convert_xml_to_loca(self, xml_path: Path, loca_path: Path) -> ProcessingResult:
        """Convertit XML en LOCA"""
        try:
            cmd = [
                str(self.divine_path),
                "-g", "bg3",
                "--action", "convert-loca",
                "--source", str(xml_path.resolve()),
                "--destination", str(loca_path.resolve())
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
            
            if loca_path.exists():
                return ProcessingResult(
                    success=True,
                    message=f"Conversion XML->LOCA réussie: {xml_path} -> {loca_path}"
                )
            else:
                return ProcessingResult(
                    success=False,
                    message="Conversion échouée: fichier LOCA non créé"
                )
                
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur de conversion XML->LOCA: {e}"
            )

# ============================================================================
# MAIN TRANSLATOR ENGINE
# ============================================================================

class BG3ModTranslator:
    """Moteur principal de traduction des mods BG3"""
    
    def __init__(self, config: TranslationConfig, divine_path: Path, deepl_key: str,
                 rules_config_path: Optional[Path] = None, glossary_manager=None):
        self.config = config
        self.divine_manager = DivineToolsManager(divine_path)
        self.rule_engine = RuleEngine()
        self.glossary_manager = glossary_manager
        
        # Chargement des règles si spécifiées
        if rules_config_path and rules_config_path.exists():
            self.rule_engine.load_rules(rules_config_path)
        
        # Initialisation du processeur de traduction
        self.translator = DeepLTranslator(
            deepl_key, config, self.rule_engine, glossary_manager
        )
        
        # Gestionnaires de fichiers
        self.file_handlers = [XMLFileHandler()]
    
    def translate_mod(self, mod_zip: Path, output_path: Path, translation_author: str,
                     mod_suffix: str = "_FR", openrouter_key: Optional[str] = None) -> ProcessingResult:
        """Traduit un mod complet"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # 1. Extraction du ZIP source
                extract_result = self._extract_mod_zip(mod_zip, temp_path)
                if not extract_result.success:
                    return extract_result
                
                # 2. Localisation et extraction du PAK
                pak_result = self._process_pak_extraction(temp_path)
                if not pak_result.success:
                    return pak_result
                
                work_dir = pak_result.data["work_directory"]
                original_metadata = pak_result.data["metadata"]
                
                # 3. Traduction des fichiers de localisation
                translation_result = self._translate_localization_files(
                    work_dir, {"openrouter_key": openrouter_key}
                )
                if not translation_result.success:
                    return translation_result
                
                # 4. Mise à jour des métadonnées
                metadata_result = self._update_mod_metadata(
                    work_dir, temp_path, original_metadata, 
                    translation_author, mod_suffix
                )
                if not metadata_result.success:
                    return metadata_result
                
                # 5. Repackaging et génération du ZIP final
                final_result = self._create_final_package(
                    work_dir, temp_path, output_path, mod_suffix
                )
                
                return final_result
                
            except Exception as e:
                return ProcessingResult(
                    success=False,
                    message=f"Erreur fatale lors de la traduction: {e}"
                )
    
    def _extract_mod_zip(self, mod_zip: Path, temp_path: Path) -> ProcessingResult:
        """Extrait le ZIP du mod"""
        try:
            with zipfile.ZipFile(mod_zip, 'r') as z:
                z.extractall(temp_path)
            
            return ProcessingResult(
                success=True,
                message="Extraction du ZIP réussie"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors de l'extraction du ZIP: {e}"
            )
    
    def _process_pak_extraction(self, temp_path: Path) -> ProcessingResult:
        """Localise et extrait le fichier PAK"""
        try:
            # Recherche des fichiers requis
            pak_files = list(temp_path.rglob("*.pak"))
            info_file = temp_path / "info.json"
            
            if not pak_files:
                return ProcessingResult(
                    success=False,
                    message="Aucun fichier PAK trouvé dans le ZIP"
                )
            
            if not info_file.exists():
                return ProcessingResult(
                    success=False,
                    message="Fichier info.json manquant"
                )
            
            pak_file = pak_files[0]
            work_directory = temp_path / "unpacked"
            
            # Extraction du PAK
            extract_result = self.divine_manager.extract_pak(pak_file, work_directory)
            if not extract_result.success:
                return extract_result
            
            # Lecture des métadonnées
            metadata = ModMetadata.from_info_json(info_file)
            
            return ProcessingResult(
                success=True,
                message="Extraction PAK réussie",
                data={
                    "work_directory": work_directory,
                    "pak_file": pak_file,
                    "metadata": metadata
                }
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors du traitement PAK: {e}"
            )
    
    def _translate_localization_files(self, work_dir: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Traduit les fichiers de localisation"""
        try:
            # Gestion du répertoire de localisation
            french_dir = work_dir / "Localization" / "French"
            english_dir = work_dir / "Localization" / "English"
            
            # Déplacement English -> French
            if english_dir.exists():
                if french_dir.exists():
                    shutil.rmtree(french_dir)
                shutil.move(str(english_dir), str(french_dir))
            else:
                french_dir.mkdir(parents=True, exist_ok=True)
            
            # Conversion LOCA en XML si nécessaire
            self._convert_loca_to_xml(french_dir)
            
            # Recherche des fichiers XML à traduire
            xml_files = list(french_dir.rglob("*.xml"))
            if not xml_files:
                return ProcessingResult(
                    success=False,
                    message="Aucun fichier XML trouvé pour la traduction"
                )
            
            # Traduction parallèle ou séquentielle
            if self.config.parallel_translation and len(xml_files) > 1:
                results = self._translate_files_parallel(xml_files, context)
            else:
                results = self._translate_files_sequential(xml_files, context)
            
            # Génération des fichiers LOCA si demandée
            if self.config.emit_loca_files:
                self._generate_loca_files(french_dir)
            
            success_count = sum(1 for r in results if r.success)
            
            return ProcessingResult(
                success=success_count > 0,
                message=f"Traduction terminée: {success_count}/{len(xml_files)} fichiers traduits",
                data={"translated_files": success_count, "total_files": len(xml_files)}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors de la traduction: {e}"
            )
    
    def _translate_files_parallel(self, xml_files: List[Path], context: Dict[str, Any]) -> List[ProcessingResult]:
        """Traduction parallèle des fichiers"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self._translate_single_file, xml_file, context): xml_file
                for xml_file in xml_files
            }
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if result.success:
                    logger.info(f"✓ {futures[future].name}")
                else:
                    logger.error(f"✗ {futures[future].name}: {result.message}")
        
        return results
    
    def _translate_files_sequential(self, xml_files: List[Path], context: Dict[str, Any]) -> List[ProcessingResult]:
        """Traduction séquentielle des fichiers"""
        results = []
        
        for xml_file in xml_files:
            result = self._translate_single_file(xml_file, context)
            results.append(result)
            
            if result.success:
                logger.info(f"✓ {xml_file.name}")
            else:
                logger.error(f"✗ {xml_file.name}: {result.message}")
        
        return results
    
    def _translate_single_file(self, xml_file: Path, context: Dict[str, Any]) -> ProcessingResult:
        """Traduit un fichier unique"""
        for handler in self.file_handlers:
            if handler.can_handle(xml_file):
                return handler.process_file(xml_file, self.translator)
        
        return ProcessingResult(
            success=False,
            message=f"Aucun gestionnaire disponible pour {xml_file}"
        )
    
    def _convert_loca_to_xml(self, localization_dir: Path) -> None:
        """Convertit les fichiers LOCA en XML"""
        loca_files = list(localization_dir.rglob("*.loca"))
        
        for loca_file in loca_files:
            if loca_file.stat().st_size > 0:  # Ignorer les fichiers vides
                xml_path = loca_file.with_suffix('.xml')
                result = self.divine_manager.convert_xml_to_loca(loca_file, xml_path)  # Note: l'API est inversée
                if result.success:
                    logger.info(f"Conversion LOCA->XML: {loca_file.name}")
    
    def _generate_loca_files(self, localization_dir: Path) -> None:
        """Génère les fichiers LOCA depuis les XML traduits"""
        xml_files = list(localization_dir.rglob("*.xml"))
        
        for xml_file in xml_files:
            loca_path = xml_file.with_suffix('.loca')
            result = self.divine_manager.convert_xml_to_loca(xml_file, loca_path)
            if result.success:
                logger.info(f"Génération LOCA: {xml_file.name}")
    
    def _update_mod_metadata(self, work_dir: Path, temp_path: Path, 
                           original_metadata: ModMetadata, author: str, suffix: str) -> ProcessingResult:
        """Met à jour les métadonnées du mod"""
        try:
            # Mise à jour meta.lsx
            for meta_file in work_dir.rglob("meta.lsx"):
                self._update_meta_lsx(meta_file, author, suffix, original_metadata)
            
            # Mise à jour info.json
            info_file = temp_path / "info.json"
            self._update_info_json(info_file, author, suffix, original_metadata)
            
            return ProcessingResult(
                success=True,
                message="Métadonnées mises à jour"
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors de la mise à jour des métadonnées: {e}"
            )
    
    def _update_meta_lsx(self, meta_path: Path, author: str, suffix: str, 
                        original_metadata: ModMetadata) -> None:
        """Met à jour le fichier meta.lsx"""
        try:
            with open(meta_path, "rb") as f:
                raw = f.read()
                encoding = chardet.detect(raw).get("encoding") or "utf-8"
            
            with open(meta_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Parse XML en supprimant la déclaration XML
            content_clean = re.sub(r'^<\?xml.*?\?>', '', content, flags=re.DOTALL)
            root = ET.fromstring(content_clean)
            
            # Mise à jour des métadonnées
            for node in root.findall(".//node[@id='ModuleInfo']"):
                # Auteur
                author_elem = node.find(".//attribute[@id='Author']")
                if author_elem is not None:
                    author_elem.set('value', author)
                
                # Nom du mod
                name_elem = node.find(".//attribute[@id='Name']")
                if name_elem is not None:
                    current_name = name_elem.get('value') or original_metadata.name
                    name_elem.set('value', current_name + suffix)
                
                # Description
                desc_elem = node.find(".//attribute[@id='Description']")
                if desc_elem is not None:
                    desc_elem.set('value', 
                        f"Traduction française du mod « {original_metadata.name} » de {original_metadata.author}.")
                
                # UUID unique
                uuid_elem = node.find(".//attribute[@id='UUID']")
                if uuid_elem is not None:
                    uuid_elem.set('value', str(uuid.uuid4()))
            
            # Sauvegarde
            xml_declaration = f'<?xml version="1.0" encoding="{encoding}"?>'
            xml_content = ET.tostring(root, encoding=encoding).decode(encoding)
            
            with open(meta_path, 'w', encoding=encoding) as f:
                f.write(xml_declaration + '\n' + xml_content)
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de meta.lsx: {e}")
    
    def _update_info_json(self, info_path: Path, author: str, suffix: str, 
                         original_metadata: ModMetadata) -> None:
        """Met à jour le fichier info.json"""
        try:
            with open(info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['Name'] = original_metadata.name.replace(" ", "") + suffix
            data['Folder'] = original_metadata.name.replace(" ", "") + suffix
            data['Author'] = author
            data['Description'] = f"Traduction française du mod « {original_metadata.name} » de {original_metadata.author}."
            data['UUID'] = str(uuid.uuid4())
            data['Group'] = str(uuid.uuid4())
            
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour d'info.json: {e}")
    
    def _create_final_package(self, work_dir: Path, temp_path: Path, 
                            output_path: Path, suffix: str) -> ProcessingResult:
        """Crée le package final"""
        try:
            # Recherche du nom original du PAK
            pak_files = list(temp_path.rglob("*.pak"))
            if not pak_files:
                return ProcessingResult(
                    success=False,
                    message="Fichier PAK original introuvable"
                )
            
            original_pak = pak_files[0]
            french_pak_name = f"{original_pak.stem}{suffix}.pak"
            french_pak_path = temp_path / french_pak_name
            
            # Création du PAK traduit
            pak_result = self.divine_manager.create_pak(work_dir, french_pak_path)
            if not pak_result.success:
                return pak_result
            
            # Détermination du chemin de sortie final
            if output_path.suffix.lower() == '.zip':
                final_zip = output_path
            else:
                output_path.mkdir(parents=True, exist_ok=True)
                final_zip = output_path / f"{original_pak.stem}{suffix}.zip"
            
            # Création du ZIP final
            with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
                z.write(french_pak_path, french_pak_name)
                z.write(temp_path / "info.json", "info.json")
            
            return ProcessingResult(
                success=True,
                message=f"Package final créé: {final_zip}",
                data={"output_file": final_zip}
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"Erreur lors de la création du package final: {e}"
            )
    
    def get_translation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de traduction"""
        return {
            "cache_stats": self.translator.cache.get_stats(),
            "config": {
                "source_lang": self.config.source_lang,
                "target_lang": self.config.target_lang,
                "use_llm": self.config.use_llm_optimization,
                "parallel": self.config.parallel_translation
            }
        }

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@contextmanager
def temporary_directory():
    """Context manager pour répertoire temporaire"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def validate_environment(divine_path: Path, deepl_key: str) -> List[str]:
    """Valide l'environnement d'exécution"""
    errors = []
    
    if not divine_path.exists():
        errors.append(f"Divine.exe introuvable: {divine_path}")
    
    if not deepl_key:
        errors.append("Clé API DeepL manquante")
    
    try:
        import deepl
        translator = deepl.Translator(auth_key=deepl_key)
        translator.get_usage()
    except Exception as e:
        errors.append(f"Erreur de connexion DeepL: {e}")
    
    return errors

def load_configuration(config_path: Optional[Path] = None) -> TranslationConfig:
    """Charge la configuration depuis un fichier ou utilise les valeurs par défaut"""
    if config_path and config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return TranslationConfig(
                source_lang=config_data.get("source_lang", "EN"),
                target_lang=config_data.get("target_lang", "FR"),
                use_llm_optimization=config_data.get("use_llm_optimization", False),
                emit_loca_files=config_data.get("emit_loca_files", False),
                clear_cache=config_data.get("clear_cache", False),
                parallel_translation=config_data.get("parallel_translation", True),
                max_workers=config_data.get("max_workers", 4)
            )
        except Exception as e:
            logger.warning(f"Erreur lors du chargement de la configuration: {e}")
    
    return TranslationConfig()

# ============================================================================
# CLI INTERFACE
# ============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Crée le parser d'arguments en ligne de commande"""
    parser = argparse.ArgumentParser(
        description="BG3 Mod Translator - Professional Translation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Traduction basique
  python bg3_translator.py --mod mod.zip --divine divine.exe --deepl-key KEY --author "Translator" --output output/
  
  # Traduction avec optimisation LLM
  python bg3_translator.py --mod mod.zip --divine divine.exe --deepl-key KEY --author "Translator" --output output.zip --use-llm --openrouter-key KEY
  
  # Traduction avec règles personnalisées
  python bg3_translator.py --mod mod.zip --divine divine.exe --deepl-key KEY --author "Translator" --output output/ --rules-config rules.json
        """
    )
    
    # Arguments principaux
    parser.add_argument("--mod", required=True, type=Path,
                       help="Fichier ZIP du mod à traduire")
    parser.add_argument("--divine", required=True, type=Path,
                       help="Chemin vers divine.exe")
    parser.add_argument("--deepl-key", required=True,
                       help="Clé API DeepL")
    parser.add_argument("--author", required=True,
                       help="Nom de l'auteur de la traduction")
    parser.add_argument("--output", required=True, type=Path,
                       help="Répertoire de sortie ou fichier ZIP final")
    
    # Configuration
    parser.add_argument("--suffix", default="_FR",
                       help="Suffixe ajouté au nom du mod traduit")
    parser.add_argument("--config", type=Path,
                       help="Fichier de configuration JSON")
    parser.add_argument("--rules-config", type=Path,
                       help="Fichier de règles de traduction JSON")
    parser.add_argument("--glossary-config", type=Path,
                       help="Fichier de configuration du glossaire")
    
    # Options de traduction
    parser.add_argument("--use-llm", action="store_true",
                       help="Active l'optimisation LLM post-traduction")
    parser.add_argument("--openrouter-key",
                       help="Clé API OpenRouter pour l'optimisation LLM")
    parser.add_argument("--emit-loca", action="store_true",
                       help="Génère les fichiers LOCA")
    parser.add_argument("--clear-cache", action="store_true",
                       help="Vide le cache de traduction")
    parser.add_argument("--no-parallel", action="store_true",
                       help="Désactive la traduction parallèle")
    
    # Options de débogage
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Mode verbeux")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulation sans modification")
    
    return parser

def setup_logging(verbose: bool = False) -> None:
    """Configure le système de logging"""
    level = logging.DEBUG if verbose else logging.INFO
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    logger.setLevel(level)
    logger.handlers.clear()
    logger.addHandler(handler)

def main():
    """Point d'entrée principal"""
    # Chargement des variables d'environnement
    load_dotenv()
    
    # Parse des arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging(args.verbose)
    
    try:
        # Validation de l'environnement
        deepl_key = args.deepl_key or os.getenv('DEEPL_API_KEY')
        openrouter_key = args.openrouter_key or os.getenv('OPENROUTER_API_KEY')
        
        validation_errors = validate_environment(args.divine, deepl_key)
        if validation_errors:
            for error in validation_errors:
                logger.error(error)
            return 1
        
        # Chargement de la configuration
        config = load_configuration(args.config)
        
        # Override de la configuration avec les arguments CLI
        config.use_llm_optimization = args.use_llm
        config.emit_loca_files = args.emit_loca
        config.clear_cache = args.clear_cache
        config.parallel_translation = not args.no_parallel
        
        # Initialisation du glossaire (si disponible)
        glossary_manager = None
        try:
            if args.glossary_config:
                # Tentative de chargement du gestionnaire de glossaire externe
                from glossary_manager import GlossaryManager
                glossary_manager = GlossaryManager()
                glossary_manager.load_custom_terms(args.glossary_config)
            else:
                # Utilisation du gestionnaire par défaut
                from glossary_manager import GlossaryManager
                glossary_manager = GlossaryManager()
        except ImportError:
            logger.warning("Gestionnaire de glossaire non disponible")
        
        # Initialisation du traducteur principal
        translator = BG3ModTranslator(
            config=config,
            divine_path=args.divine,
            deepl_key=deepl_key,
            rules_config_path=args.rules_config,
            glossary_manager=glossary_manager
        )
        
        # Mode dry-run
        if args.dry_run:
            logger.info("Mode simulation - Aucune modification ne sera effectuée")
            return 0
        
        # Traduction du mod
        logger.info(f"Démarrage de la traduction: {args.mod}")
        
        result = translator.translate_mod(
            mod_zip=args.mod,
            output_path=args.output,
            translation_author=args.author,
            mod_suffix=args.suffix,
            openrouter_key=openrouter_key
        )
        
        # Rapport de résultats
        if result.success:
            logger.info(f"✓ Traduction réussie: {result.message}")
            
            # Affichage des statistiques
            stats = translator.get_translation_stats()
            logger.info(f"Statistiques de cache: {stats['cache_stats']}")
            
            return 0
        else:
            logger.error(f"✗ Traduction échouée: {result.message}")
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
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit(main())