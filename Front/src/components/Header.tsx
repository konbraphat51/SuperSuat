import { FetchSession } from "../scripts/SessionControl";

export const Header = () => {
	const session = FetchSession();

	return (
		<header style={{ padding: "16px 20px", borderBottom: "1px solid #ddd", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
			<div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
				<h1 style={{ margin: 0, fontSize: "20px" }}>
					<a href="/" style={{ textDecoration: "none", color: "inherit" }}>SuperSuat</a>
				</h1>
				<nav style={{ display: "flex", gap: "16px" }}>
					<a href="/documents" style={{ textDecoration: "none", color: "#4a90d9" }}>ドキュメント一覧</a>
				</nav>
			</div>
			<div>
				{session.isLoggedIn ? (
					<>
						<span style={{ marginRight: "12px" }}>{session.userName}</span>
						<button onClick={() => (window.location.href = "/.auth/logout")}>Logout</button>
					</>
				) : (
					<button onClick={() => (window.location.href = "/.auth/login/github")}>
						Login with GitHub
					</button>
				)}
			</div>
		</header>
	);
};
