#!/usr/bin/env python3
"""
Safety Manager - File safety operations for PDF processing
Handles hashing, collision detection, backups, and validation.
"""

import hashlib
import shutil
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SafetyManager:
    """
    Handles file safety operations for PDF processing.
    
    Features:
    - SHA256 hash validation
    - Collision detection
    - Automatic backup creation
    - Confirmation prompts
    - File integrity checking
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize safety manager with configuration."""
        self.config = config or {}
        
        # Safety settings
        self.create_backup = self.config.get('create_backup', True)
        self.require_confirmation = self.config.get('require_confirmation', True)
        self.hash_validation = self.config.get('hash_validation', True)
        self.backup_suffix = self.config.get('backup_suffix', '.backup')
        self.max_backup_count = self.config.get('max_backup_count', 5)
        
        logger.debug(f"Safety Manager initialized with backup={self.create_backup}, "
                    f"confirmation={self.require_confirmation}, hash={self.hash_validation}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash as hexadecimal string
        """
        if not file_path.exists():
            return ""
        
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def detect_collision(self, source_file: Path, target_file: Path) -> bool:
        """
        Check if target file would create a collision.
        
        Args:
            source_file: Source file path
            target_file: Target file path that might be overwritten
            
        Returns:
            True if collision detected, False otherwise
        """
        if not target_file.exists():
            return False
        
        # If files have the same name but different content, it's a collision
        if source_file.name == target_file.name:
            source_hash = self.calculate_file_hash(source_file)
            target_hash = self.calculate_file_hash(target_file)
            
            if source_hash and target_hash and source_hash != target_hash:
                logger.warning(f"Collision detected: {target_file} exists with different content")
                return True
        
        return False
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """
        Create backup of existing file.
        
        Args:
            file_path: Path to file to backup
            
        Returns:
            Path to backup file if successful, None otherwise
        """
        if not file_path.exists():
            return None
        
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{self.backup_suffix}{file_path.suffix}"
            backup_path = file_path.parent / backup_name
            
            # Handle multiple backups with same timestamp
            counter = 1
            while backup_path.exists():
                backup_name = f"{file_path.stem}_{timestamp}_{counter}{self.backup_suffix}{file_path.suffix}"
                backup_path = file_path.parent / backup_name
                counter += 1
            
            # Create backup
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            
            # Cleanup old backups if needed
            self._cleanup_old_backups(file_path)
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def _cleanup_old_backups(self, original_file: Path) -> None:
        """Remove old backup files to stay within max_backup_count."""
        try:
            # Find all backup files for this original file
            backup_pattern = f"{original_file.stem}_*{self.backup_suffix}{original_file.suffix}"
            backup_files = list(original_file.parent.glob(backup_pattern))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove excess backups
            for old_backup in backup_files[self.max_backup_count:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Could not remove old backup {old_backup}: {e}")
                    
        except Exception as e:
            logger.warning(f"Error cleaning up old backups: {e}")
    
    def confirm_overwrite(self, file_path: Path) -> bool:
        """
        Get user confirmation for file overwrite.
        
        Args:
            file_path: Path to file that would be overwritten
            
        Returns:
            True if user confirms, False otherwise
        """
        if not self.require_confirmation:
            return True
        
        if not file_path.exists():
            return True
        
        try:
            file_info = file_path.stat()
            file_size = file_info.st_size
            mod_time = datetime.fromtimestamp(file_info.st_mtime)
            
            print(f"\n⚠️  File exists: {file_path}")
            print(f"   Size: {file_size:,} bytes")
            print(f"   Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            response = input("   Overwrite? [y/N]: ").lower().strip()
            return response in ['y', 'yes']
            
        except Exception as e:
            logger.error(f"Error getting confirmation: {e}")
            # Default to safe choice
            return False
    
    def safe_write_check(self, source_file: Path, target_file: Path) -> Tuple[bool, str]:
        """
        Comprehensive safety check before writing.
        
        Args:
            source_file: Source file being processed
            target_file: Target file that will be written
            
        Returns:
            Tuple of (can_proceed, reason)
        """
        # Check for collision
        if self.detect_collision(source_file, target_file):
            return False, f"Collision detected: {target_file} exists with different content"
        
        # Check for overwrite confirmation
        if target_file.exists():
            if not self.confirm_overwrite(target_file):
                return False, "User cancelled overwrite"
            
            # Create backup if enabled
            if self.create_backup:
                backup_path = self.create_backup(target_file)
                if backup_path:
                    logger.info(f"Backup created: {backup_path}")
                else:
                    logger.warning("Could not create backup")
        
        # Validate source file
        if not source_file.exists():
            return False, f"Source file does not exist: {source_file}"
        
        # Check if target directory is writable
        target_dir = target_file.parent
        if not target_dir.exists():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create target directory: {e}"
        
        if not os.access(target_dir, os.W_OK):
            return False, f"Target directory not writable: {target_dir}"
        
        return True, "Safe to proceed"
    
    def validate_file_integrity(self, file_path: Path, 
                               expected_hash: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate file integrity.
        
        Args:
            file_path: Path to file to validate
            expected_hash: Optional expected hash to compare against
            
        Returns:
            Tuple of (is_valid, validation_info)
        """
        if not file_path.exists():
            return False, {"error": "File does not exist"}
        
        try:
            # Basic file stats
            file_stats = file_path.stat()
            validation_info = {
                "file_size": file_stats.st_size,
                "modification_time": datetime.fromtimestamp(file_stats.st_mtime),
                "is_readable": os.access(file_path, os.R_OK),
                "file_hash": None,
                "hash_match": None
            }
            
            # Calculate hash if validation enabled
            if self.hash_validation:
                current_hash = self.calculate_file_hash(file_path)
                validation_info["file_hash"] = current_hash
                
                if expected_hash:
                    validation_info["hash_match"] = (current_hash == expected_hash)
                    if not validation_info["hash_match"]:
                        logger.warning(f"Hash mismatch for {file_path}")
                        logger.warning(f"Expected: {expected_hash}")
                        logger.warning(f"Actual:   {current_hash}")
                        return False, validation_info
            
            # Check if file is a valid PDF (basic check)
            if file_path.suffix.lower() == '.pdf':
                try:
                    with open(file_path, 'rb') as f:
                        header = f.read(8)
                        if not header.startswith(b'%PDF-'):
                            validation_info["error"] = "Not a valid PDF file"
                            return False, validation_info
                except Exception as e:
                    validation_info["error"] = f"Could not read PDF header: {e}"
                    return False, validation_info
            
            validation_info["status"] = "valid"
            return True, validation_info
            
        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")
            return False, {"error": str(e)}
    
    def get_safe_output_path(self, base_path: Path, prefix: str = "", 
                           suffix: str = "") -> Path:
        """
        Generate a safe output path that doesn't conflict with existing files.
        
        Args:
            base_path: Base path for output file
            prefix: Optional prefix to add
            suffix: Optional suffix to add
            
        Returns:
            Safe output path
        """
        # Build filename
        stem = base_path.stem
        if prefix:
            stem = f"{prefix}_{stem}"
        if suffix:
            stem = f"{stem}_{suffix}"
        
        output_path = base_path.parent / f"{stem}{base_path.suffix}"
        
        # If file doesn't exist, we're good
        if not output_path.exists():
            return output_path
        
        # Find available numbered variant
        counter = 1
        while output_path.exists():
            numbered_stem = f"{stem}_{counter}"
            output_path = base_path.parent / f"{numbered_stem}{base_path.suffix}"
            counter += 1
            
            # Safety limit to prevent infinite loop
            if counter > 9999:
                raise ValueError("Could not find available output filename")
        
        return output_path
    
    def verify_operation_success(self, source_file: Path, target_file: Path,
                               operation: str = "conversion") -> bool:
        """
        Verify that an operation completed successfully.
        
        Args:
            source_file: Original source file
            target_file: Created target file
            operation: Description of operation performed
            
        Returns:
            True if operation appears successful, False otherwise
        """
        try:
            # Check that target file was created
            if not target_file.exists():
                logger.error(f"{operation} failed: target file not created")
                return False
            
            # Check that target file has reasonable size
            target_size = target_file.stat().st_size
            if target_size == 0:
                logger.error(f"{operation} failed: target file is empty")
                return False
            
            # For same-format operations, compare sizes for reasonableness
            if source_file.suffix == target_file.suffix:
                source_size = source_file.stat().st_size
                size_ratio = target_size / source_size if source_size > 0 else 0
                
                # Very small or very large size changes might indicate problems
                if size_ratio < 0.1 or size_ratio > 10:
                    logger.warning(f"{operation} size change seems unusual: "
                                 f"{source_size} -> {target_size} bytes")
            
            logger.info(f"{operation} verification passed: {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying {operation}: {e}")
            return False


# Import os for file permission checks
import os