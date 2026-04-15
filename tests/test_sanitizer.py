from app.services.sanitizer import PiiSanitizer


class TestPiiSanitizer:
    def setup_method(self):
        self.sanitizer = PiiSanitizer()

    def test_mask_cpf(self):
        data = {"tax_id": "123.456.789-00"}
        result = self.sanitizer.sanitize(data)
        assert result["tax_id"] == "***.***789-00"

    def test_mask_cpf_digits_only(self):
        data = {"cpf": "12345678900"}
        result = self.sanitizer.sanitize(data)
        assert result["cpf"] == "***.***678900"

    def test_mask_cnpj(self):
        data = {"cnpj": "20.018.183/0001-80"}
        result = self.sanitizer.sanitize(data)
        assert result["cnpj"] == "**.***.***/0001-80"

    def test_mask_email(self):
        data = {"email": "joao@email.com"}
        result = self.sanitizer.sanitize(data)
        assert result["email"] == "j***@email.com"

    def test_mask_short_email(self):
        data = {"email": "ab@x.com"}
        result = self.sanitizer.sanitize(data)
        assert result["email"] == "**@x.com"

    def test_mask_name(self):
        data = {"name": "Joao Silva"}
        result = self.sanitizer.sanitize(data)
        assert result["name"] == "J**o S***a"

    def test_mask_phone(self):
        data = {"whatsapp": "+5511999887766"}
        result = self.sanitizer.sanitize(data)
        assert result["whatsapp"].endswith("7766")
        assert "***" in result["whatsapp"]

    def test_non_sensitive_keys_untouched(self):
        data = {"amount": 5000, "status": "created", "bank_code": "001"}
        result = self.sanitizer.sanitize(data)
        assert result == data

    def test_nested_dict(self):
        data = {"invoice": {"name": "Maria Santos", "amount": 1000}}
        result = self.sanitizer.sanitize(data)
        assert result["invoice"]["name"] == "M***a S****s"
        assert result["invoice"]["amount"] == 1000

    def test_list_of_dicts(self):
        data = {"invoices": [{"name": "Ana", "amount": 100}, {"name": "Bob", "amount": 200}]}
        result = self.sanitizer.sanitize(data)
        assert result["invoices"][0]["name"] == "A*a"
        assert result["invoices"][0]["amount"] == 100

    def test_custom_sensitive_keys(self):
        sanitizer = PiiSanitizer(sensitive_keys={"secret_field"})
        data = {"secret_field": "sensitive", "name": "Not Masked"}
        result = sanitizer.sanitize(data)
        assert result["name"] == "Not Masked"
        assert result["secret_field"] != "sensitive"
