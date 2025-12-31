import { initializeApp, type FirebaseApp } from "firebase/app";
import {
	getFirestore,
	collection,
	doc,
	getDoc,
	getDocs,
	setDoc,
	updateDoc,
	deleteDoc,
	serverTimestamp,
	type Firestore,
	type DocumentReference,
} from "firebase/firestore";

// Firebase configuration - loaded from environment variables
// These should be set in your deployment environment
const firebaseConfig = {
	apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
	authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "",
	projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "",
	storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "",
	messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "",
	appId: import.meta.env.VITE_FIREBASE_APP_ID || "",
};

// Initialize Firebase
let app: FirebaseApp | null = null;
let db: Firestore | null = null;

export const initializeFirebase = (): Firestore => {
	if (!app) {
		app = initializeApp(firebaseConfig);
	}
	if (!db) {
		db = getFirestore(app);
	}
	return db;
};

export const getDb = (): Firestore => {
	if (!db) {
		return initializeFirebase();
	}
	return db;
};

// Types for Firestore data
export interface DocumentMetadata {
	id: string;
	title: string;
	pageCount: number;
	createdAt?: Date;
	updatedAt?: Date;
}

export interface PageData {
	number: number;
	width: number;
	height: number;
	paragraphs: ParagraphData[];
}

export interface ParagraphData {
	polygon: number[];
	role: string;
	content: string;
	paragraph_index: number;
}

export interface HighlightData {
	id: string;
	documentId: string;
	paragraphIndex: number;
	startOffset: number;
	endOffset: number;
	color: [number, number, number];
	memo: string;
	createdAt?: Date;
	updatedAt?: Date;
}

// Document operations
export const fetchDocuments = async (): Promise<DocumentMetadata[]> => {
	const firestore = getDb();
	const documentsRef = collection(firestore, "documents");
	const snapshot = await getDocs(documentsRef);

	return snapshot.docs.map((doc) => {
		const data = doc.data();
		return {
			id: doc.id,
			title: data.title || "Untitled",
			pageCount: data.pageCount || 0,
			createdAt: data.createdAt?.toDate?.() || undefined,
			updatedAt: data.updatedAt?.toDate?.() || undefined,
		};
	});
};

export const fetchDocument = async (
	docId: string
): Promise<DocumentMetadata | null> => {
	const firestore = getDb();
	const docRef = doc(firestore, "documents", docId);
	const snapshot = await getDoc(docRef);

	if (!snapshot.exists()) {
		return null;
	}

	const data = snapshot.data();
	return {
		id: snapshot.id,
		title: data.title || "Untitled",
		pageCount: data.pageCount || 0,
		createdAt: data.createdAt?.toDate?.() || undefined,
		updatedAt: data.updatedAt?.toDate?.() || undefined,
	};
};

export const fetchDocumentPages = async (docId: string): Promise<PageData[]> => {
	const firestore = getDb();
	const pagesRef = collection(firestore, "documents", docId, "pages");
	const snapshot = await getDocs(pagesRef);

	return snapshot.docs
		.map((doc) => {
			const data = doc.data();
			return {
				number: data.number,
				width: data.width,
				height: data.height,
				paragraphs: data.paragraphs || [],
			};
		})
		.sort((a, b) => a.number - b.number);
};

// Highlight operations
export const fetchHighlights = async (docId: string): Promise<HighlightData[]> => {
	const firestore = getDb();
	const highlightsRef = collection(firestore, "documents", docId, "highlights");
	const snapshot = await getDocs(highlightsRef);

	return snapshot.docs.map((doc) => {
		const data = doc.data();
		return {
			id: doc.id,
			documentId: docId,
			paragraphIndex: data.paragraphIndex,
			startOffset: data.startOffset,
			endOffset: data.endOffset,
			color: data.color || [255, 255, 0],
			memo: data.memo || "",
			createdAt: data.createdAt?.toDate?.() || undefined,
			updatedAt: data.updatedAt?.toDate?.() || undefined,
		};
	});
};

export const createHighlight = async (
	docId: string,
	highlight: Omit<HighlightData, "id" | "documentId" | "createdAt" | "updatedAt">
): Promise<string> => {
	const firestore = getDb();
	const highlightsRef = collection(firestore, "documents", docId, "highlights");
	const newDocRef = doc(highlightsRef);

	await setDoc(newDocRef, {
		...highlight,
		createdAt: serverTimestamp(),
		updatedAt: serverTimestamp(),
	});

	return newDocRef.id;
};

export const updateHighlight = async (
	docId: string,
	highlightId: string,
	updates: Partial<Pick<HighlightData, "memo" | "color">>
): Promise<void> => {
	const firestore = getDb();
	const highlightRef = doc(
		firestore,
		"documents",
		docId,
		"highlights",
		highlightId
	);

	await updateDoc(highlightRef, {
		...updates,
		updatedAt: serverTimestamp(),
	});
};

export const deleteHighlight = async (
	docId: string,
	highlightId: string
): Promise<void> => {
	const firestore = getDb();
	const highlightRef = doc(
		firestore,
		"documents",
		docId,
		"highlights",
		highlightId
	);

	await deleteDoc(highlightRef);
};

export {
	collection,
	doc,
	getDoc,
	getDocs,
	setDoc,
	updateDoc,
	deleteDoc,
	serverTimestamp,
	type DocumentReference,
};
