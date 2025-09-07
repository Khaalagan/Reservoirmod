#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Rules Manager - Système d'auto-amélioration pour les règles de traduction
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

@dataclass
class Rule:
    """Représente une règle de traduction"""
    name: str
    pattern: str
    replacement: str
    description: str
    stage: str  # pre_translation, post_translation, final_cleanup
    confidence: float = 1.0
    usage_count: int = 0
    success_rate: float = 1.0
    created_at: Optional[datetime] = None
    mod_specific: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la règle en dictionnaire"""
        return {
            "name": self.name,
            "pattern": self.pattern,
            "replacement": self.replacement, 
            "description": self.description,
            "stage": self.stage,
            "confidence": self.confidence,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "mod_specific": self.mod_specific
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """Crée une règle depuis un dictionnaire"""
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass
        
        return cls(
            name=data["name"],
            pattern=data["pattern"],
            replacement=data["replacement"],
            description=data["description"],
            stage=data["stage"],
            confidence=data.get("confidence", 1.0),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 1.0),
            created_at=created_at,
            mod_specific=data.get("mod_specific")
        )

@dataclass
class LearningCandidate:
    """Candidat pour l'apprentissage automatique"""
    source_text: str
    original_translation: str
    improved_translation: str
    improvement_source: str  # "llm", "manual", "pattern_detection"
    confidence: float
    frequency: int = 1
    detected_pattern: Optional[str] = None
    suggested_replacement: Optional[str] = None

class DynamicRulesManager:
    """Gestionnaire de règles dynamiques avec capacité d'auto-amélioration"""
    
    def __init__(self, base_rules_path: Path, learned_rules_path: Optional[Path] = None):
        self.base_rules_path = base_rules_path
        self.learned_rules_path = learned_rules_path or base_rules_path.parent / "learned_rules.json"
        
        # Stockage des règles
        self.base_rules: Dict[str, List[Rule]] = defaultdict(list)
        self.learned_rules: Dict[str, List[Rule]] = defaultdict(list)
        self.mod_specific_rules: Dict[str, Dict[str, List[Rule]]] = defaultdict(lambda: defaultdict(list))
        
        # Système d'apprentissage
        self.learning_candidates: List[LearningCandidate] = []
        self.pattern_frequency: Counter = Counter()
        self.error_patterns: Dict[str, int] = defaultdict(int)
        
        # Configuration
        self.learning_config = {
            "enabled": True,
            "auto_improve": True,
            "confidence_threshold": 0.8,
            "max_learned_rules": 100,
            "min_frequency_for_pattern": 3,
            "similarity_threshold": 0.9
        }
        
        # Charger les règles existantes
        self._load_base_rules()
        self._load_learned_rules()
    
    def _load_base_rules(self) -> None:
        """Charge les règles de base depuis le fichier de configuration"""
        try:
            with open(self.base_rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Charger les règles par stade
            for stage in ["pre_translation", "post_translation", "final_cleanup"]:
                if stage in data:
                    for rule_data in data[stage]:
                        rule = Rule(
                            name=rule_data["name"],
                            pattern=rule_data["pattern"], 
                            replacement=rule_data["replacement"],
                            description=rule_data["description"],
                            stage=stage
                        )
                        self.base_rules[stage].append(rule)
            
            # Charger la configuration d'apprentissage
            if "learning_rules" in data:
                self.learning_config.update(data["learning_rules"])
            
            logger.info(f"Règles de base chargées: {self.base_rules_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des règles de base: {e}")
    
    def _load_learned_rules(self) -> None:
        """Charge les règles apprises"""
        if not self.learned_rules_path.exists():
            return
        
        try:
            with open(self.learned_rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for stage_data in data.get("learned_rules", {}).values():
                for rule_data in stage_data:
                    rule = Rule.from_dict(rule_data)
                    self.learned_rules[rule.stage].append(rule)
            
            # Charger les candidats d'apprentissage
            for candidate_data in data.get("learning_candidates", []):
                candidate = LearningCandidate(
                    source_text=candidate_data["source_text"],
                    original_translation=candidate_data["original_translation"],
                    improved_translation=candidate_data["improved_translation"],
                    improvement_source=candidate_data["improvement_source"],
                    confidence=candidate_data["confidence"],
                    frequency=candidate_data.get("frequency", 1),
                    detected_pattern=candidate_data.get("detected_pattern"),
                    suggested_replacement=candidate_data.get("suggested_replacement")
                )
                self.learning_candidates.append(candidate)
            
            logger.info(f"Règles apprises chargées: {len(self.learned_rules)} règles")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des règles apprises: {e}")
    
    def load_mod_specific_rules(self, mod_name: str, rules_path: Path) -> bool:
        """Charge les règles spécifiques à un mod"""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for stage in ["pre_translation", "post_translation", "final_cleanup"]:
                if stage in data:
                    for rule_data in data[stage]:
                        rule = Rule(
                            name=rule_data["name"],
                            pattern=rule_data["pattern"],
                            replacement=rule_data["replacement"], 
                            description=rule_data["description"],
                            stage=stage,
                            mod_specific=mod_name
                        )
                        self.mod_specific_rules[mod_name][stage].append(rule)
            
            logger.info(f"Règles spécifiques chargées pour {mod_name}: {rules_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des règles pour {mod_name}: {e}")
            return False
    
    def get_applicable_rules(self, stage: str, mod_name: Optional[str] = None) -> List[Rule]:
        """Récupère toutes les règles applicables pour un stade donné"""
        rules = []
        
        # Règles de base
        rules.extend(self.base_rules[stage])
        
        # Règles apprises
        rules.extend(self.learned_rules[stage])
        
        # Règles spécifiques au mod
        if mod_name and mod_name in self.mod_specific_rules:
            rules.extend(self.mod_specific_rules[mod_name][stage])
        
        # Trier par confiance décroissante
        rules.sort(key=lambda r: r.confidence, reverse=True)
        
        return rules
    
    def apply_rules(self, text: str, stage: str, mod_name: Optional[str] = None) -> str:
        """Applique les règles à un texte pour un stade donné"""
        if not text:
            return text
        
        result = text
        applicable_rules = self.get_applicable_rules(stage, mod_name)
        
        for rule in applicable_rules:
            try:
                old_result = result
                result = re.sub(rule.pattern, rule.replacement, result, flags=re.IGNORECASE)
                
                # Mise à jour des statistiques d'usage
                if old_result != result:
                    rule.usage_count += 1
                    logger.debug(f"Règle appliquée '{rule.name}': '{old_result}' -> '{result}'")
                
            except re.error as e:
                logger.warning(f"Erreur regex dans la règle '{rule.name}': {e}")
                rule.success_rate *= 0.9  # Pénalise les règles avec erreurs
        
        return result
    
    def learn_from_llm_improvement(self, source_text: str, original_translation: str, 
                                  improved_translation: str, confidence: float = 0.8) -> bool:
        """Apprend à partir d'une amélioration LLM"""
        if not self.learning_config["enabled"]:
            return False
        
        # Éviter les doublons
        for candidate in self.learning_candidates:
            if (candidate.source_text == source_text and 
                candidate.original_translation == original_translation):
                candidate.frequency += 1
                candidate.confidence = max(candidate.confidence, confidence)
                return True
        
        # Détecter le pattern d'amélioration
        detected_pattern, suggested_replacement = self._detect_improvement_pattern(
            original_translation, improved_translation
        )
        
        # Créer un nouveau candidat
        candidate = LearningCandidate(
            source_text=source_text,
            original_translation=original_translation,
            improved_translation=improved_translation,
            improvement_source="llm",
            confidence=confidence,
            detected_pattern=detected_pattern,
            suggested_replacement=suggested_replacement
        )
        
        self.learning_candidates.append(candidate)
        
        # Évaluation immédiate si assez confiant
        if (confidence >= self.learning_config["confidence_threshold"] and 
            self.learning_config["auto_improve"]):
            self._evaluate_learning_candidates()
        
        return True
    
    def _detect_improvement_pattern(self, original: str, improved: str) -> Tuple[Optional[str], Optional[str]]:
        """Détecte le pattern d'amélioration entre deux textes"""
        # Analyse des différences pour détecter des patterns récurrents
        
        # Différences de mots
        original_words = original.split()
        improved_words = improved.split()
        
        if len(original_words) == len(improved_words):
            # Chercher les substitutions directes
            for i, (orig_word, impr_word) in enumerate(zip(original_words, improved_words)):
                if orig_word != impr_word:
                    # Pattern potentiel détecté
                    pattern = f"\\b{re.escape(orig_word)}\\b"
                    replacement = impr_word
                    return pattern, replacement
        
        # Chercher des patterns plus complexes avec difflib
        matcher = SequenceMatcher(None, original, improved)
        opcodes = matcher.get_opcodes()
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'replace' and i2-i1 > 2 and j2-j1 > 2:  # Substitutions significatives
                orig_segment = original[i1:i2].strip()
                impr_segment = improved[j1:j2].strip()
                
                if orig_segment and impr_segment:
                    pattern = re.escape(orig_segment)
                    replacement = impr_segment
                    return pattern, replacement
        
        return None, None
    
    def _evaluate_learning_candidates(self) -> None:
        """Évalue les candidats d'apprentissage et crée de nouvelles règles"""
        if not self.learning_candidates:
            return
        
        # Grouper les candidats par pattern détecté
        pattern_groups = defaultdict(list)
        for candidate in self.learning_candidates:
            if candidate.detected_pattern:
                pattern_groups[candidate.detected_pattern].append(candidate)
        
        # Évaluer chaque groupe
        for pattern, candidates in pattern_groups.items():
            total_frequency = sum(c.frequency for c in candidates)
            avg_confidence = sum(c.confidence * c.frequency for c in candidates) / total_frequency
            
            # Critères pour créer une nouvelle règle
            if (total_frequency >= self.learning_config["min_frequency_for_pattern"] and
                avg_confidence >= self.learning_config["confidence_threshold"]):
                
                # Prendre le remplacement le plus fréquent
                replacements = Counter(c.suggested_replacement for c in candidates 
                                     if c.suggested_replacement)
                if replacements:
                    most_common_replacement = replacements.most_common(1)[0][0]
                    
                    # Créer la nouvelle règle
                    self._create_learned_rule(pattern, most_common_replacement, candidates)
    
    def _create_learned_rule(self, pattern: str, replacement: str, 
                           candidates: List[LearningCandidate]) -> None:
        """Crée une nouvelle règle apprise"""
        # Déterminer le stade optimal (par défaut post_translation)
        stage = "post_translation"
        
        # Générer un nom unique
        rule_name = f"learned_{len(self.learned_rules[stage])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculer la confiance moyenne
        total_freq = sum(c.frequency for c in candidates)
        avg_confidence = sum(c.confidence * c.frequency for c in candidates) / total_freq
        
        # Description basée sur les candidats
        sources = set(c.improvement_source for c in candidates)
        description = f"Règle apprise automatiquement (sources: {', '.join(sources)}, fréquence: {total_freq})"
        
        # Créer la règle
        rule = Rule(
            name=rule_name,
            pattern=pattern,
            replacement=replacement,
            description=description,
            stage=stage,
            confidence=avg_confidence,
            usage_count=0,
            success_rate=1.0
        )
        
        self.learned_rules[stage].append(rule)
        
        # Nettoyer les candidats utilisés
        for candidate in candidates:
            if candidate in self.learning_candidates:
                self.learning_candidates.remove(candidate)
        
        logger.info(f"Nouvelle règle apprise: {rule_name} ({pattern} -> {replacement})")
        
        # Sauvegarder immédiatement
        self.save_learned_rules()
    
    def save_learned_rules(self) -> bool:
        """Sauvegarde les règles apprises"""
        try:
            # Nettoyer les règles les moins performantes si trop nombreuses
            self._cleanup_learned_rules()
            
            data = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_learned_rules": sum(len(rules) for rules in self.learned_rules.values()),
                    "learning_config": self.learning_config
                },
                "learned_rules": {
                    stage: [rule.to_dict() for rule in rules] 
                    for stage, rules in self.learned_rules.items()
                },
                "learning_candidates": [
                    {
                        "source_text": c.source_text,
                        "original_translation": c.original_translation,
                        "improved_translation": c.improved_translation,
                        "improvement_source": c.improvement_source,
                        "confidence": c.confidence,
                        "frequency": c.frequency,
                        "detected_pattern": c.detected_pattern,
                        "suggested_replacement": c.suggested_replacement
                    }
                    for c in self.learning_candidates
                ]
            }
            
            self.learned_rules_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.learned_rules_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Règles apprises sauvegardées: {self.learned_rules_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des règles apprises: {e}")
            return False
    
    def _cleanup_learned_rules(self) -> None:
        """Nettoie les règles apprises les moins performantes"""
        max_rules = self.learning_config["max_learned_rules"]
        
        for stage in self.learned_rules:
            rules = self.learned_rules[stage]
            if len(rules) > max_rules:
                # Trier par score (combinaison de confiance, usage et succès)
                def rule_score(rule: Rule) -> float:
                    return rule.confidence * (1 + rule.usage_count) * rule.success_rate
                
                rules.sort(key=rule_score, reverse=True)
                
                # Garder seulement les meilleures
                removed_count = len(rules) - max_rules
                self.learned_rules[stage] = rules[:max_rules]
                
                logger.info(f"Nettoyage des règles {stage}: {removed_count} règles supprimées")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'apprentissage"""
        total_learned = sum(len(rules) for rules in self.learned_rules.values())
        total_base = sum(len(rules) for rules in self.base_rules.values())
        
        return {
            "base_rules": total_base,
            "learned_rules": total_learned,
            "learning_candidates": len(self.learning_candidates),
            "learning_enabled": self.learning_config["enabled"],
            "auto_improve": self.learning_config["auto_improve"],
            "rules_by_stage": {
                stage: len(rules) for stage, rules in self.learned_rules.items()
            },
            "top_patterns": self.pattern_frequency.most_common(10)
        }
    
    def export_rules_for_review(self, output_path: Path) -> bool:
        """Exporte les règles apprises pour révision humaine"""
        try:
            review_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_rules": sum(len(rules) for rules in self.learned_rules.values()),
                    "review_instructions": "Révisez chaque règle et marquez approved=true/false"
                },
                "rules_for_review": []
            }
            
            for stage, rules in self.learned_rules.items():
                for rule in rules:
                    review_data["rules_for_review"].append({
                        **rule.to_dict(),
                        "approved": None,  # À remplir par le réviseur
                        "review_notes": ""  # Notes du réviseur
                    })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(review_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Règles exportées pour révision: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'export pour révision: {e}")
            return False
    
    def import_reviewed_rules(self, reviewed_path: Path) -> int:
        """Importe les règles révisées et approuvées"""
        try:
            with open(reviewed_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            approved_count = 0
            rejected_count = 0
            
            for rule_data in data.get("rules_for_review", []):
                if rule_data.get("approved") is True:
                    rule = Rule.from_dict(rule_data)
                    # Mettre à jour la règle existante ou l'ajouter
                    stage_rules = self.learned_rules[rule.stage]
                    
                    # Chercher si la règle existe déjà
                    existing_rule = None
                    for existing in stage_rules:
                        if existing.name == rule.name:
                            existing_rule = existing
                            break
                    
                    if existing_rule:
                        # Mettre à jour avec les modifications du réviseur
                        existing_rule.pattern = rule.pattern
                        existing_rule.replacement = rule.replacement
                        existing_rule.description = rule.description
                        existing_rule.confidence = rule.confidence
                    else:
                        stage_rules.append(rule)
                    
                    approved_count += 1
                    
                elif rule_data.get("approved") is False:
                    # Supprimer la règle rejetée
                    rule_name = rule_data["name"]
                    stage = rule_data["stage"]
                    
                    self.learned_rules[stage] = [
                        r for r in self.learned_rules[stage] 
                        if r.name != rule_name
                    ]
                    rejected_count += 1
            
            # Sauvegarder les changements
            if approved_count > 0 or rejected_count > 0:
                self.save_learned_rules()
            
            logger.info(f"Révision importée: {approved_count} approuvées, {rejected_count} rejetées")
            return approved_count
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import de révision: {e}")
            return 0