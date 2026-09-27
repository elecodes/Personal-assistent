"""Firebase Client module for Voice Task & Notes persistence.

Handles Cloud Firestore (text/metadata storage) and Firebase Storage (audio file storage).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional, Dict, List

import firebase_admin
from firebase_admin import credentials, firestore, storage

logger = logging.getLogger("firebase_client")

class FirebaseManager:
    """Manager for Firebase Firestore and Storage operations."""

    def __init__(self, credentials_path: Optional[str] = None, storage_bucket: Optional[str] = None):
        self.credentials_path = credentials_path or os.getenv("FIREBASE_CREDENTIALS_PATH")
        self.storage_bucket_name = storage_bucket or os.getenv("FIREBASE_STORAGE_BUCKET")
        self._db = None
        self._bucket = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the Firebase Admin SDK."""
        if self._initialized:
            return True

        try:
            if firebase_admin._apps:
                app = firebase_admin.get_app()
            elif self.credentials_path and os.path.exists(self.credentials_path):
                cred = credentials.Certificate(self.credentials_path)
                options = {}
                if self.storage_bucket_name:
                    options["storageBucket"] = self.storage_bucket_name
                app = firebase_admin.initialize_app(cred, options)
            else:
                logger.warning("No FIREBASE_CREDENTIALS_PATH set or file does not exist. Firebase operating in uninitialized state.")
                return False

            self._db = firestore.client()
            if self.storage_bucket_name:
                self._bucket = storage.bucket()
            self._initialized = True
            logger.info("Firebase Admin SDK successfully initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            return False

    @property
    def db(self):
        if not self._initialized:
            self.initialize()
        return self._db

    def save_note(
        self,
        title: str,
        content: str,
        category: str = "Nota",
        priority: str = "Media",
        audio_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Save a new note/task document into Firestore.
        
        Returns the created document ID.
        """
        if not self.db:
            logger.error("Cannot save note: Firestore database not initialized.")
            return None

        doc_data = {
            "title": title,
            "content": content,
            "category": category,
            "priority": priority,
            "audio_url": audio_url,
            "tags": tags or [],
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        try:
            doc_ref = self.db.collection("notes").document()
            doc_ref.set(doc_data)
            logger.info(f"Note saved successfully with ID: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error saving note to Firestore: {e}")
            return None

    def get_notes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent notes from Firestore."""
        if not self.db:
            logger.error("Cannot fetch notes: Firestore database not initialized.")
            return []

        try:
            notes_ref = self.db.collection("notes").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            docs = notes_ref.stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            return results
        except Exception as e:
            logger.error(f"Error fetching notes from Firestore: {e}")
            return []

    def upload_audio_file(self, local_file_path: str, remote_file_name: Optional[str] = None) -> Optional[str]:
        """Upload an audio file to Firebase Storage and return its public URL."""
        if not self._initialized:
            self.initialize()

        if not self._bucket:
            logger.error("Cannot upload audio: Firebase Storage bucket not configured.")
            return None

        if not os.path.exists(local_file_path):
            logger.error(f"File not found: {local_file_path}")
            return None

        file_name = remote_file_name or f"audio_notes/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.path.basename(local_file_path)}"
        try:
            blob = self._bucket.blob(file_name)
            blob.upload_from_filename(local_file_path)
            blob.make_public()
            logger.info(f"Audio uploaded successfully: {blob.public_url}")
            return blob.public_url
        except Exception as e:
            logger.error(f"Error uploading audio file to Firebase Storage: {e}")
            return None


# Global instance
firebase_manager = FirebaseManager()
