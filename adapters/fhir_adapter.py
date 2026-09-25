from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any

class FhirAdapter:
    @staticmethod
    def to_context(
        patient_resource: Dict[str, Any], 
        observation_resource: Dict[str, Any], 
        reference_date: date = None,
        allergy_resource: Optional[Dict[str, Any]] = None,
        medication_resource: Optional[Dict[str, Any]] = None,
        dispense_resource: Optional[Dict[str, Any]] = None,
        encounter_resource: Optional[Dict[str, Any]] = None
    ) -> dict:
        if reference_date is None:
            raise ValueError("reference_date is required for deterministic evaluation")
            
        # 1. Mapear Patient
        birth_date_str = patient_resource.get("birthDate")
        if not birth_date_str:
            raise ValueError("Patient resource missing 'birthDate'")
            
        birth_date = date.fromisoformat(birth_date_str)
        age = reference_date.year - birth_date.year - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))
        active = patient_resource.get("active")
        
        # 2. Mapear Observation
        obs_coding = observation_resource.get("code", {}).get("coding", [])
        obs_code = obs_coding[0].get("code") if obs_coding else None
        obs_value = observation_resource.get("valueQuantity", {}).get("value")
        if obs_value is not None:
            obs_value = Decimal(str(obs_value))
            
        context = {
            "patient": {"age": age, "active": active},
            "observation": {"code": obs_code, "value": obs_value}
        }
        
        # 3. Mapear AllergyIntolerance (Opcional)
        if allergy_resource is not None:
            allergy_coding = allergy_resource.get("code", {}).get("coding", [])
            allergy_code = allergy_coding[0].get("code") if allergy_coding else None
            allergy_status_coding = allergy_resource.get("clinicalStatus", {}).get("coding", [])
            allergy_status = allergy_status_coding[0].get("code") if allergy_status_coding else None
            
            context["allergy"] = {
                "code": allergy_code,
                "status": allergy_status
            }
            
        # 4. Mapear MedicationRequest (Opcional)
        if medication_resource is not None:
            med_coding = medication_resource.get("medicationCodeableConcept", {}).get("coding", [])
            med_code = med_coding[0].get("code") if med_coding else None
            med_status = medication_resource.get("status")
            
            context["medication"] = {
                "code": med_code,
                "status": med_status
            }
            
        # 5. Mapear MedicationDispense (Opcional)
        if dispense_resource is not None:
            dispense_coding = dispense_resource.get("medicationCodeableConcept", {}).get("coding", [])
            dispense_code = dispense_coding[0].get("code") if dispense_coding else None
            dispense_status = dispense_resource.get("status")
            
            context["dispense"] = {
                "code": dispense_code,
                "status": dispense_status
            }
            
        # 6. Mapear Encounter (Opcional)
        if encounter_resource is not None:
            enc_status = encounter_resource.get("status")
            enc_class = encounter_resource.get("class", {}).get("code")
            
            context["encounter"] = {
                "status": enc_status,
                "class": enc_class
            }
            
        return context
