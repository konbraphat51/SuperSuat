"""
CLI to upload extracted OCR document data to Firestore.

Usage:
    python -m Suat.DataControl.FirestoreUploader --data-file <path> --doc-id <id> --title <title> [--credentials <path>]

Arguments:
    --data-file, -d     Path to the extracted OCR data JSON file
    --doc-id, -i        Document ID to use in Firestore
    --title, -t         Document title
    --credentials, -c   Path to Firebase service account credentials JSON (optional if GOOGLE_APPLICATION_CREDENTIALS is set)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore


def initialize_firebase(credentials_path: str | None = None) -> firestore.firestore.Client:
    """
    Initialize Firebase Admin SDK and return Firestore client.
    
    Args:
        credentials_path: Optional path to service account credentials JSON file.
                          If not provided, uses GOOGLE_APPLICATION_CREDENTIALS env var.
    
    Returns:
        Firestore client instance.
    """
    try:
        # Check if app is already initialized
        firebase_admin.get_app()
    except ValueError:
        # App not initialized, initialize it
        if credentials_path:
            cred = credentials.Certificate(credentials_path)
        else:
            # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
            cred = credentials.ApplicationDefault()
        
        firebase_admin.initialize_app(cred)
    
    return firestore.client()


def upload_document_data(
    db: firestore.firestore.Client,
    doc_id: str,
    title: str,
    ocr_data: dict[str, Any],
) -> None:
    """
    Upload document data to Firestore.
    
    Args:
        db: Firestore client instance.
        doc_id: Document ID to use in Firestore.
        title: Document title.
        ocr_data: Extracted OCR data containing pages and paragraphs.
    """
    # Create main document entry
    doc_ref = db.collection("documents").document(doc_id)
    
    # Prepare document metadata
    doc_metadata = {
        "id": doc_id,
        "title": title,
        "pageCount": len(ocr_data.get("pages", [])),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }
    
    # Store document metadata
    doc_ref.set(doc_metadata)
    print(f"Created document: {doc_id}")
    
    # Store pages data in subcollection
    pages_collection = doc_ref.collection("pages")
    for page in ocr_data.get("pages", []):
        page_number = page["number"]
        page_ref = pages_collection.document(str(page_number))
        page_ref.set({
            "number": page_number,
            "width": page["width"],
            "height": page["height"],
            "paragraphs": page.get("paragraphs", []),
        })
        print(f"  Uploaded page {page_number}")
    
    # Create empty highlights subcollection document (placeholder)
    highlights_ref = doc_ref.collection("highlights")
    # We don't create any highlight documents initially - they will be created by the frontend
    
    print(f"Document '{title}' (ID: {doc_id}) uploaded successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload extracted OCR document data to Firestore."
    )
    parser.add_argument(
        "--data-file", "-d",
        required=True,
        help="Path to the extracted OCR data JSON file"
    )
    parser.add_argument(
        "--doc-id", "-i",
        required=True,
        help="Document ID to use in Firestore"
    )
    parser.add_argument(
        "--title", "-t",
        required=True,
        help="Document title"
    )
    parser.add_argument(
        "--credentials", "-c",
        default=None,
        help="Path to Firebase service account credentials JSON (optional)"
    )
    
    args = parser.parse_args()
    
    # Validate data file exists
    if not os.path.exists(args.data_file):
        print(f"Error: Data file not found: {args.data_file}", file=sys.stderr)
        sys.exit(1)
    
    # Load OCR data
    try:
        with open(args.data_file, "r", encoding="utf-8") as f:
            ocr_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in data file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize Firebase and upload
    try:
        db = initialize_firebase(args.credentials)
        upload_document_data(db, args.doc_id, args.title, ocr_data)
    except Exception as e:
        print(f"Error uploading to Firestore: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
