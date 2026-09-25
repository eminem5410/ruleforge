from datetime import date
from decimal import Decimal

class FhirAdapter:
    @staticmethod
    def to_context(patient_resource: dict, observation_resource: dict, reference_date: date = None) -> dict:
        if reference_date is None:
            raise ValueError("reference_date is required for deterministic evaluation")
            
        # Mapear Patient
        birth_date_str = patient_resource.get("birthDate")
        if not birth_date_str:
            raise ValueError("Patient resource missing 'birthDate'")
            
        birth_date = date.fromisoformat(birth_date_str)
        age = reference_date.year - birth_date.year - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))
        
        # Si 'active' no está, usamos None (NULL) en lugar de False silencioso
        active = patient_resource.get("active")
        
        # Mapear Observation
        code_coding = observation_resource.get("code", {}).get("coding", [])
        obs_code = code_coding[0].get("code") if code_coding else None
        
        value_quantity = observation_resource.get("valueQuantity", {})
        obs_value = value_quantity.get("value")
        
        # Preservar Decimal nativo si viene como string o int, no convertir a float
        if obs_value is not None:
            obs_value = Decimal(str(obs_value))
        
        return {
            "patient": {"age": age, "active": active},
            "observation": {"code": obs_code, "value": obs_value}
        }
