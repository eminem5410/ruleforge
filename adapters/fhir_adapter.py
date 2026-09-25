from datetime import date

class FhirAdapter:
    @staticmethod
    def to_context(patient_resource: dict, observation_resource: dict) -> dict:
        # Mapear Patient
        birth_date_str = patient_resource.get("birthDate")
        birth_date = date.fromisoformat(birth_date_str)
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        
        active = patient_resource.get("active", False)
        
        # Mapear Observation
        code_coding = observation_resource.get("code", {}).get("coding", [])
        obs_code = code_coding[0].get("code") if code_coding else None
        
        value_quantity = observation_resource.get("valueQuantity", {})
        obs_value = value_quantity.get("value")
        
        return {
            "patient": {"age": age, "active": active},
            "observation": {"code": obs_code, "value": float(obs_value) if obs_value else None}
        }
