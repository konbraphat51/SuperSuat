const PATH_SESSION = "/.auth/me";

export interface Session {
	isLoggedIn: boolean;
	userId: string | null;
	userName: string | null;
}

interface AuthResponse {
	clientPrincipal: {
		identityProvider: string;
		userId: string;
		userDetails: string;
		userRoles: string[];
	} | null;
}

export const FetchSession = (): Session => {
	try {
		// Make synchronous fetch request
		const xhr = new XMLHttpRequest();
		xhr.open("GET", PATH_SESSION, false); // false makes it synchronous
		xhr.send();

		if (xhr.status === 200) {
			const response: AuthResponse = JSON.parse(xhr.responseText);

			if (response.clientPrincipal) {
				// User is logged in
				return {
					isLoggedIn: true,
					userId: response.clientPrincipal.userId,
					userName: response.clientPrincipal.userDetails,
				};
			} else {
				// User is logged out
				return {
					isLoggedIn: false,
					userId: null,
					userName: null,
				};
			}
		} else {
			// Request failed, assume not logged in
			return {
				isLoggedIn: false,
				userId: null,
				userName: null,
			};
		}
	} catch (error) {
		// Error occurred, assume not logged in
		console.error("Error checking login status:", error);
		return {
			isLoggedIn: false,
			userId: null,
			userName: null,
		};
	}
};
