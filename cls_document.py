class DocumentId:
    """Клас формування зведених даних про окремий документ"""
    blank_number = None
    date_created = None
    date_expired = None
    pass_office = None
    expired_status = None
    non_office_starts = ['Номер', 'Дата', 'Дійсний', 'необмежений', 'Документ', 'Паспорт(и)']

    def __init__(self, blank, date1, date2, status, office):
        self.blank_number = blank
        self.date_created = date1
        self.date_expired = date2
        self.pass_office = office
        self.expired_status = status

    def __str__(self):
        return str(self.blank_number) + " (" \
               + str(self.date_created) + " - " \
               + str(self.date_expired) + ")" \
               + str(self.pass_office)
