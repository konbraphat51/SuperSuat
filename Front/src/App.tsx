import { BrowserRouter, Routes, Route } from "react-router-dom";
import { PageHome } from "./components/pages/home/PageHome";
import { PageLogin } from "./components/pages/login/PageLogin";

function App() {
	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={<PageHome />} />
				<Route path="/login" element={<PageLogin />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;
