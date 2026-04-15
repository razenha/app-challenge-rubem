import re



# Helper para sanitizar dados pessoais, para poder logar e persistir dados de forma segura.
class PiiSanitizer:
    DEFAULT_SENSITIVE_KEYS = {
        "name", "nome",
        "tax_id", "taxid", "tax-id",
        "document", "documento",
        "cpf", "cnpj",
        "email", "e-mail",
        "phone", "telefone", "whatsapp",
    }

    def __init__(self, sensitive_keys=None):
        self.sensitive_keys = sensitive_keys or self.DEFAULT_SENSITIVE_KEYS

    def sanitize(self, data):
        if isinstance(data, dict):
            return {k: self._sanitize_value(k, v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.sanitize(item) for item in data]
        return data

    def _sanitize_value(self, key, value):
        if isinstance(value, dict):
            return self.sanitize(value)
        if isinstance(value, list):
            return [self.sanitize(item) for item in value]
        if isinstance(value, str) and self._is_sensitive(key):
            return self._mask(key, value)
        return value

    def _is_sensitive(self, key):
        return key.lower() in self.sensitive_keys

    def _mask(self, key, value):
        key_lower = key.lower()

        if key_lower in {"cpf", "tax_id", "taxid", "tax-id", "document", "documento", "cnpj"}:
            return self._mask_document(value)
        if key_lower in {"email", "e-mail"}:
            return self._mask_email(value)
        if key_lower in {"phone", "telefone", "whatsapp"}:
            return self._mask_phone(value)
        if key_lower in {"name", "nome"}:
            return self._mask_name(value)

        return self._mask_generic(value)

    def _mask_document(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11:
            return f"***.***{value[-6:]}"
        if len(digits) == 14:
            return f"**.***.***{value[-8:]}"
        return self._mask_generic(value)

    def _mask_email(self, value):
        parts = value.split("@")
        if len(parts) != 2:
            return self._mask_generic(value)
        local = parts[0]
        domain = parts[1]
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 1)
        return f"{masked_local}@{domain}"

    def _mask_phone(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) < 4:
            return "*" * len(value)
        return "*" * (len(digits) - 4) + digits[-4:]

    def _mask_name(self, value):
        parts = value.split()
        masked = []
        for part in parts:
            if len(part) <= 2:
                masked.append("*" * len(part))
            else:
                masked.append(part[0] + "*" * (len(part) - 2) + part[-1])
        return " ".join(masked)

    def _mask_generic(self, value):
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
