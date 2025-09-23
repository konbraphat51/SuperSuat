import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Header } from "./components/Header";
import { PageHome } from "./components/pages/home/PageHome";
import { PageLogin } from "./components/pages/login/PageLogin";

function App() {
	return (
		<>
			<Header />
			<BrowserRouter>
				<Routes>
					<Route path="/" element={<PageHome />} />
					<Route path="/login" element={<PageLogin />} />
				</Routes>
			</BrowserRouter>
		</>
	);
}

export default App;
