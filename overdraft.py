def r2(x):
    return round(x, 2)


class Overdraft:
    def __init__(self, limit=3000.0, annual_interest=0.24):
        self.limit = limit
        self.balance = 0.0
        self.monthly_rate = annual_interest / 12
        self.exceeded = False

    def cover_deficit(self, cash):
        self.exceeded = False

        if cash >= 0:
            return cash

        needed = -cash

        if self.balance + needed > self.limit:
            self.exceeded = True
            self.balance = r2(self.limit)
            return 0.0

        self.balance = r2(self.balance + needed)
        return 0.0

    def repay(self, cash):
        return r2(cash)

    def apply_interest(self):
        return 0.0

    def get_state(self):
        return {
            "balance": self.balance,
            "limit": self.limit
        }
