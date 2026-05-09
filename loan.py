# loan.py
def r2(x):
    return round(x, 2)


class Loan:
    def __init__(self, balance, annual_interest, months):
        self.balance = r2(balance)
        self.monthly_rate = annual_interest / 12
        self.months = months
        self.arrears = 0.0

        # -------------------------
        # FIXED PAYMENT (SCENARIO)
        # -------------------------
        self.fixed_payment = 330.0

    # -------------------------
    # INTEREST
    # -------------------------
    def apply_interest(self):
        if self.balance <= 0:
            return 0.0
        return r2(self.balance * self.monthly_rate)

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

        interest = self.apply_interest()
        required = self.fixed_payment

        # arrears
        if amount < required:
            self.arrears = r2(self.arrears + (required - amount))

        # payment split
        principal_paid = r2(amount - interest)
        if principal_paid < 0:
            principal_paid = 0.0

        # reduce balance
        self.balance = r2(self.balance - principal_paid)
        if self.balance < 0:
            self.balance = 0.0

        return {
            "interest": interest,
            "principal": principal_paid
        }

    # -------------------------
    # STATE
    # -------------------------
    def get_state(self):
        return {
            "balance": self.balance,
            "arrears": self.arrears,
            "required_payment": self.get_required_payment()
        }