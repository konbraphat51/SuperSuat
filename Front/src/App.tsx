import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { PageHome } from "./components/pages/home/PageHome";
import { PageLogin } from "./components/pages/login/PageLogin";
import { OriginCreation } from "./components/pages/OriginCreation/OriginCreation";

function App() {
	return (
		<>
			<Header />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<PageHome />} />
					<Route path="/login" element={<PageLogin />} />
					<Route path="/origin-creation" element={<OriginCreation />} />
				</Routes>
			</BrowserRouter>
			<Footer />
		</>
	);
}

export default App;
