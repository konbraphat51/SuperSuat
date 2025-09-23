import { FetchSession } from "../scripts/SessionControl";

export const Header = () => {
	const session = FetchSession();

	return (
		<header>
			<h1>Welcome to SuperSuat</h1>
			{session.isLoggedIn ? (
				<>
					<p>You are logged in as {session.userName}</p>
					<button onClick={() => (window.location.href = "/.auth/logout")}>Logout</button>
				</>
			) : (
				<button onClick={() => (window.location.href = "/.auth/login/github")}>
					Login with GitHub
				</button>
			)}
		</header>
	);
};
