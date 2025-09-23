import { FetchSession } from "../../../scripts/SessionControl";

export const PageHome = () => {
	const session = FetchSession();

	return (
		<div>
			<h1>Home</h1>
		</div>
	);
};
