import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { PageHome } from "./components/pages/home/PageHome";
import { PageLogin } from "./components/pages/login/PageLogin";
import { PagePdfOrdering } from "./components/pages/pdfOrdering/PagePdfOrdering";

function App() {
	return (
		<>
			<Header />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<PageHome />} />
					<Route path="/login" element={<PageLogin />} />
					<Route path="/ordering" element={<PagePdfOrdering />} />
				</Routes>
			</BrowserRouter>
			<Footer />
		</>
	);
}

export default App;
