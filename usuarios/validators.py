import re
from django.core.exceptions import ValidationError

class ComplejidadPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r'[a-z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra minúscula.")
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe contener al menos un número.")
        if not re.search(r'[@$!%*?&._\-#]', password):
            raise ValidationError("La contraseña debe contener al menos un carácter especial (ej: @, $, !, %, *, o ?).")

    def get_help_text(self):
        return "Tu contraseña debe tener al menos 8 caracteres, incluyendo una mayúscula, una minúscula, un número y un carácter especial."
