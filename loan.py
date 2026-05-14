# loan.py
def r2(x):
    return round(x, 2)


class Loan:
    def __init__(self, balance, annual_interest, months):
        self.balance = r2(balance)
        self.monthly_rate = annual_interest / 12
        self.months = months
        self.arrears = 0.0

        # Monthly reference value shown to the participant.
        self.fixed_payment = 317.71

    # -------------------------
    # INTEREST
    # -------------------------
    def apply_interest(self):
        return 0.0

    # -------------------------
    # REQUIRED PAYMENT (FIXED)
    # -------------------------
    def get_required_payment(self):
        if self.balance <= 0:
            return 0.0
        return self.fixed_payment

    # -------------------------
    # APPLY PAYMENT
    # -------------------------
    def apply_payment(self, amount):
        if self.balance <= 0:
            return {"interest": 0.0, "principal": 0.0}

        principal_paid = min(r2(max(amount, 0.0)), self.balance)

        self.balance = r2(self.balance - principal_paid)
        if self.balance < 0:
            self.balance = 0.0

        return {
            "interest": 0.0,
            "principal": principal_paid
        }

    # -------------------------
    # STATE
    # -------------------------
    def get_state(self):
        return {
            "balance": self.balance,
            "required_payment": self.get_required_payment()
        }
