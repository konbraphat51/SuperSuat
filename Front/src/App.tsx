import { BrowserRouter, Routes, Route } from "react-router-dom";
import { PageHome } from "./pages/home/PageHome";
import { PageLogin } from "./pages/login/PageLogin";

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
