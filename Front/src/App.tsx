import { BrowserRouter, Link, Switch, Route } from "react-router-dom";
import { PageLogin } from "./pages/login/pageLogin.tsx";

function App() {
	return (
		<BrowserRouter>
			<Switch>
				<Route path="/login" component={PageLogin} />
			</Switch>
		</BrowserRouter>
	);
}

export default App;
