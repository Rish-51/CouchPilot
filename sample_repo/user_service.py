class UserService:
    def __init__(self, db_conn, cache_ttl=300):
        self.db = db_conn
        self.cache_ttl = cache_ttl
        self._active_sessions = {}

    def get_user_by_id(self, user_id):
        return self.db.find_one({"id": user_id})

    def update_user_status(self, user_id, is_active):
        record = self.get_user_by_id(user_id)
        if not record:
            return False
        record["is_active"] = is_active
        return True

    @property
    def session_count(self):
        return len(self._active_sessions)

class AuthTokenValidator:
    def validate_token(self, token_str, secret):
        if not token_str:
            return False
        return len(token_str) > 10
