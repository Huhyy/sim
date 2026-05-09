def r2(x):
    return round(x, 2)


class Overdraft:
    def __init__(self, limit=1000.0, annual_interest=0.24):
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
            return cash

        self.balance = r2(self.balance + needed)
        return 0.0

    def repay(self, cash):
        if cash <= 0 or self.balance <= 0:
            return cash

        repay_amount = min(cash, self.balance)
        self.balance = r2(self.balance - repay_amount)
        return r2(cash - repay_amount)

    def apply_interest(self):
        interest = r2(self.balance * self.monthly_rate)
        self.balance = r2(self.balance + interest)
        return interest

    def get_state(self):
        return {
            "balance": self.balance,
            "limit": self.limit
        }