#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BlacklistManager - Verwaltet Blacklist und Whitelist für Datenschutz
"""

import json
from pathlib import Path
from typing import List, Set, Optional
import pandas as pd

from PySide6.QtCore import QObject, Signal


class BlacklistManager(QObject):
    """
    Verwaltet die Blacklist und Whitelist für sensible Begriffe.
    Unterstützt Import aus Excel und TXT-Dateien.
    """
    
    list_updated = Signal()
    
    def __init__(self, config_dir: Optional[Path] = None):
        super().__init__()
        
        self.config_dir = config_dir or Path.home() / ".explorerpro"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.blacklist_path = self.config_dir / "blacklist.json"
        self.whitelist_path = self.config_dir / "whitelist.json"
        
        self._blacklist: Set[str] = set()
        self._whitelist: Set[str] = set()
        
        self._load()
    
    # ===== Properties =====
    
    @property
    def blacklist(self) -> List[str]:
        return sorted(self._blacklist)
    
    @property
    def whitelist(self) -> List[str]:
        return sorted(self._whitelist)
    
    # ===== Laden/Speichern =====
    
    def _load(self):
        """Lädt beide Listen"""
        if self.blacklist_path.exists():
            try:
                with open(self.blacklist_path, 'r', encoding='utf-8') as f:
                    self._blacklist = set(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass

        if self.whitelist_path.exists():
            try:
                with open(self.whitelist_path, 'r', encoding='utf-8') as f:
                    self._whitelist = set(json.load(f))
            except (OSError, json.JSONDecodeError):
                pass
    
    def _save(self):
        """Speichert beide Listen"""
        try:
            with open(self.blacklist_path, 'w', encoding='utf-8') as f:
                json.dump(list(self._blacklist), f, ensure_ascii=False, indent=2)
            
            with open(self.whitelist_path, 'w', encoding='utf-8') as f:
                json.dump(list(self._whitelist), f, ensure_ascii=False, indent=2)
                
            self.list_updated.emit()
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
    
    # ===== Blacklist-Operationen =====
    
    def add_to_blacklist(self, term: str) -> bool:
        """Fügt einen Begriff zur Blacklist hinzu"""
        term = term.strip()
        if term and term not in self._blacklist:
            self._blacklist.add(term)
            self._save()
            return True
        return False
    
    def remove_from_blacklist(self, term: str) -> bool:
        """Entfernt einen Begriff aus der Blacklist"""
        if term in self._blacklist:
            self._blacklist.discard(term)
            self._save()
            return True
        return False
    
    def clear_blacklist(self):
        """Leert die Blacklist"""
        self._blacklist.clear()
        self._save()
    
    # ===== Whitelist-Operationen =====
    
    def add_to_whitelist(self, term: str) -> bool:
        """Fügt einen Begriff zur Whitelist hinzu"""
        term = term.strip()
        if term and term not in self._whitelist:
            self._whitelist.add(term)
            self._save()
            return True
        return False
    
    def remove_from_whitelist(self, term: str) -> bool:
        """Entfernt einen Begriff aus der Whitelist"""
        if term in self._whitelist:
            self._whitelist.discard(term)
            self._save()
            return True
        return False
    
    def clear_whitelist(self):
        """Leert die Whitelist"""
        self._whitelist.clear()
        self._save()
    
    # ===== Import/Export =====
    
    def import_from_file(self, filepath: str, target: str = "blacklist") -> int:
        """
        Importiert Begriffe aus einer Datei.
        Unterstützt: .txt, .csv, .xlsx
        
        Returns:
            Anzahl der importierten Begriffe
        """
        path = Path(filepath)
        if not path.exists():
            return 0
        
        terms = []
        
        try:
            if path.suffix == '.xlsx':
                df = pd.read_excel(path, header=None)
                terms = df.iloc[:, 0].astype(str).tolist()
            
            elif path.suffix == '.csv':
                df = pd.read_csv(path, header=None)
                terms = df.iloc[:, 0].astype(str).tolist()
            
            else:  # .txt und andere
                with open(path, 'r', encoding='utf-8') as f:
                    terms = [line.strip() for line in f if line.strip()]
        
        except Exception as e:
            print(f"Import-Fehler: {e}")
            return 0
        
        # Zur richtigen Liste hinzufügen
        target_set = self._blacklist if target == "blacklist" else self._whitelist
        count_before = len(target_set)
        
        for term in terms:
            term = str(term).strip()
            if term:
                target_set.add(term)
        
        count_added = len(target_set) - count_before
        self._save()
        
        return count_added
    
    def export_to_file(self, filepath: str, source: str = "blacklist") -> bool:
        """
        Exportiert eine Liste in eine Datei.
        
        Returns:
            True bei Erfolg
        """
        path = Path(filepath)
        source_list = self._blacklist if source == "blacklist" else self._whitelist
        
        try:
            if path.suffix == '.xlsx':
                df = pd.DataFrame(sorted(source_list), columns=['Begriff'])
                df.to_excel(path, index=False)
            
            elif path.suffix == '.csv':
                df = pd.DataFrame(sorted(source_list), columns=['Begriff'])
                df.to_csv(path, index=False)
            
            else:  # .txt
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(sorted(source_list)))
            
            return True
        
        except Exception as e:
            print(f"Export-Fehler: {e}")
            return False
    
    # ===== Prüfung =====
    
    def is_blacklisted(self, text: str, case_sensitive: bool = False) -> bool:
        """Prüft, ob der Text Blacklist-Begriffe enthält"""
        check_text = text if case_sensitive else text.lower()
        
        for term in self._blacklist:
            check_term = term if case_sensitive else term.lower()
            if check_term in check_text:
                return True
        return False
    
    def is_whitelisted(self, text: str, case_sensitive: bool = False) -> bool:
        """Prüft, ob der Text Whitelist-Begriffe enthält"""
        check_text = text if case_sensitive else text.lower()
        
        for term in self._whitelist:
            check_term = term if case_sensitive else term.lower()
            if check_term in check_text:
                return True
        return False
    
    def get_matching_blacklist_terms(self, text: str, case_sensitive: bool = False) -> List[str]:
        """Gibt alle im Text gefundenen Blacklist-Begriffe zurück"""
        check_text = text if case_sensitive else text.lower()
        matches = []
        
        for term in self._blacklist:
            check_term = term if case_sensitive else term.lower()
            if check_term in check_text:
                matches.append(term)
        
        return matches
    
    # ===== Statistik =====
    
    def get_stats(self) -> dict:
        """Gibt Statistiken zurück"""
        return {
            "blacklist_count": len(self._blacklist),
            "whitelist_count": len(self._whitelist)
        }
