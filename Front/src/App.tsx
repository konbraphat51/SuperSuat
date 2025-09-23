import { BrowserRouter, Routes, Route } from "react-router-dom";
import { PageHome } from "./pages/home/PageHome";

function App() {
	return (
		<BrowserRouter>
			<Routes>
				<Route path="/" element={<PageHome />} />
			</Routes>
		</BrowserRouter>
	);
}

export default App;
