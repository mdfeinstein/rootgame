from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.response import Response
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def login_client(client: APIClient, user: str, password: str):
    response = client.post("/api/token/", data={"username": user, "password": password})
    print(response.json())
    token = response.json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class RootGameClient(APIClient):
    def __init__(self, user: str, password: str, game_id: int):
        super().__init__()
        self.user = user
        self.password = password
        self.login()
        self.game_id = game_id
        self.base_route: str | None = None
        self.step: dict | None = None
        self.last_get_response: Response | None = None
        self.last_post_response: Response | None = None
        # # switches
        self.print_responses = False
        # self.assert_ok = False

    def login(self):
        response = self.post(
            "/api/token/", data={"username": self.user, "password": self.password}
        )
        token = response.json()["access"]
        refresh = response.json()["refresh"]
        self.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def get_action(self):
        """
        Client looks up current action and gets the first step of the current action
        """
        response = self.get(f"/api/game/current-action/{self.game_id}/")
        try:
            self.base_route = response.json()["route"]
        except (KeyError, TypeError) as e:
            print(
                f"Error getting current action: {response.status_code} {response.json()}"
            )
            raise e
        response = self.get(f"{self.base_route}?game_id={self.game_id}")
        self.step = response.json()
        self.last_get_response = response
        return response

    def _extract_path_and_query(self, url: str) -> tuple[str, dict]:
        """Extract path and query params from URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # Flatten query params (parse_qs returns lists for values)
        flat_params = {k: v[0] if v else '' for k, v in query_params.items()}
        return parsed.path, flat_params

    def _construct_url_with_params(self, base_path: str, **params) -> str:
        """Construct URL by combining base path with query parameters."""
        if not params:
            return base_path
        query_string = urlencode(params)
        return f"{base_path}?{query_string}"

    def post_action(self, data: dict):
        """
        Client posts data to the current action
        This sends the already processed data. To simulate a user pressing a button,
        use submit_action
        """
        if self.step is None:
            raise ValueError("No current action")
        if not self.base_route:
            raise ValueError("No base route set")

        base_path, base_params = self._extract_path_and_query(self.base_route)
        step_route = f"{base_path}{self.game_id}/{self.step['endpoint']}/"
        response = self.post(step_route, data=data, format="json")
        if self.ok(response):
            response_data = response.json()
            if response_data.get("new_base_endpoint"):
                new_base_endpoint = response_data["new_base_endpoint"]
                # Extract path and params from new redirect URL
                new_path, new_params = self._extract_path_and_query(new_base_endpoint)
                # Combine params: new_params take precedence
                all_params = {**base_params, **new_params, "game_id": self.game_id}
                get_url = self._construct_url_with_params(new_path, **all_params)
                get_response = self.get(get_url)
                self.step = get_response.json()
                # Update base_route to just the path for next iteration
                self.base_route = new_path
                self.last_get_response = get_response
                self.last_post_response = response
                return get_response
            self.step = response_data
        self.last_post_response = response
        return response

    def submit_action(self, data: dict):
        """
        This simulates the user submitting a button press,
        which the UI will package according to step info and the client will then
        send the data to the server

        data is a dict of the form data_type : data
        """
        if self.step is None:
            raise ValueError("No current action")

        if "payload_details" not in self.step:
            raise ValueError(f"Step has no payload_details: {self.step}")

        payload_details: list[dict] = self.step["payload_details"]
        # prepare data to post
        to_send = {}
        # Merge accumulated payload if exists
        acc = self.step.get("accumulated_payload")
        if acc:
            to_send.update(acc)

        # process data by picking out matching payload details
        # and naming them according to provided details
        for payload_detail in payload_details:
            if payload_detail["type"] in data:
                to_send[payload_detail["name"]] = data[payload_detail["type"]]
            else:
                raise ValueError(
                    f"{payload_detail} not found in submitted data. Available data keys: {list(data.keys())}"
                )
        # send data to endpoint
        response = self.post_action(to_send)
        if not self.ok(response):
            print("error: ", response.json())
            return response
        if response.json()["name"] == "completed":
            try:
                self.get_action()
            except Exception:
                # If no next action available, that's ok (turn might be ending)
                pass
        self.print_last_post_response()
        return response

    def ok(self, response: Response):
        return 200 <= response.status_code < 300

    def print_last_get_response(self):
        if self.last_get_response is not None and self.print_responses:
            print(self.last_get_response.json())

    def print_last_post_response(self):
        if self.last_post_response is not None and self.print_responses:
            print(self.last_post_response.json())
