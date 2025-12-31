import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { PageHome } from "./components/pages/home/PageHome";
import { PageLogin } from "./components/pages/login/PageLogin";
import { PageDocumentList } from "./components/pages/documents/PageDocumentList";
import { PageDocumentView } from "./components/pages/documents/PageDocumentView";

function App() {
	return (
		<>
			<Header />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<PageHome />} />
					<Route path="/login" element={<PageLogin />} />
					<Route path="/documents" element={<PageDocumentList />} />
					<Route path="/documents/:documentId" element={<PageDocumentView />} />
				</Routes>
			</BrowserRouter>
			<Footer />
		</>
	);
}

export default App;
