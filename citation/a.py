import os
import re
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from dataclasses import dataclass, asdict
from enum import Enum, auto

class CitationStyle(Enum):
    # US Citation Styles
    BLUEBOOK_US = "Bluebook (US)"
    ALWD = "ALWD Guide to Legal Citation"
    CHICAGO_MANUAL_LEGAL = "Chicago Manual of Legal Citation"
    
    # UK Citation Styles
    OSCOLA = "Oxford Standard Citation of Legal Authorities"
    
    # Canadian Citation Styles
    CANADIAN_GUIDE = "Canadian Guide to Uniform Legal Citation (McGill Guide)"
    
    # Australian Citation Styles
    AGLC = "Australian Guide to Legal Citation"
    AUSTLII = "AustLII Citation Format"
    
    # Indian Citation Styles
    INDIAN_LEGAL = "Indian Law Institute Citation Style"
    INDIAN_LAW_COMMISSION = "Indian Law Commission Citation Style"
    
    # European Citation Styles
    ECHR = "European Court of Human Rights Citation Style"
    ECJ = "European Court of Justice Citation Style"
    
    # International Citation Styles
    INTERNATIONAL_COURT_JUSTICE = "International Court of Justice Citation Style"
    INTERNATIONAL_CRIMINAL_COURT = "International Criminal Court Citation Style"

class JurisdictionType(Enum):
    # US Jurisdictions
    US_FEDERAL = "us_federal"
    US_STATE = "us_state"
    US_SUPREME_COURT = auto()
    US_FEDERAL_CIRCUIT = auto()
    
    # UK Jurisdictions
    UK_SUPREME_COURT = auto()
    UK_HIGH_COURT = auto()
    
    # Indian Jurisdictions
    INDIAN_SUPREME = auto()
    INDIAN_HIGH_COURT = auto()
    INDIAN_STATE = "indian_state"
    
    # European Jurisdictions
    EU_COURT_OF_JUSTICE = auto()
    EUROPEAN_COURT_HUMAN_RIGHTS = auto()
    
    # International Jurisdictions
    INTERNATIONAL_COURT_JUSTICE = auto()
    INTERNATIONAL_CRIMINAL_COURT = auto()
    
    # Australian Jurisdictions
    AU_HIGH_COURT = auto()
    AU_FEDERAL_COURT = auto()

@dataclass
class CitationValidationResult:
    """Structured result for citation validation."""
    is_valid: bool
    error_details: list[str] = None
    suggested_correction: Optional[str] = None
    source_type: Optional[str] = None
    jurisdiction: Optional[JurisdictionType] = None

    def to_dict(self):
        """Convert dataclass to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

class LegalCitationProcessor:
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("No API key provided. Set GOOGLE_API_KEY environment variable.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Citation style metadata
        self._citation_styles = {
            CitationStyle.BLUEBOOK_US: {
                "full_name": "The Bluebook: A Uniform System of Citation",
                "jurisdiction": [JurisdictionType.US_SUPREME_COURT, JurisdictionType.US_FEDERAL_CIRCUIT]
            },
            CitationStyle.OSCOLA: {
                "full_name": "Oxford Standard Citation of Legal Authorities",
                "jurisdiction": [JurisdictionType.UK_SUPREME_COURT, JurisdictionType.UK_HIGH_COURT]
            },
            CitationStyle.INDIAN_LEGAL: {
                "full_name": "Indian Law Institute Citation Style",
                "jurisdiction": [JurisdictionType.INDIAN_SUPREME, JurisdictionType.INDIAN_HIGH_COURT]
            }
        }

    def validate_citation(self, citation: str, style: CitationStyle = CitationStyle.BLUEBOOK_US) -> CitationValidationResult:
        """Validate legal citations."""
        try:
            style_info = self._citation_styles.get(style, {})
            prompt = f"""
            Analyze the legal citation '{citation}' according to {style_info.get('full_name', style.value)} rules.
            
            VALIDATION REQUIREMENTS:
            1. Check citation format
            2. Verify all required components
            3. Identify formatting errors
            4. Consider jurisdiction-specific rules
            
            Output JSON format:
            {{
                "is_valid": boolean,
                "error_details": [list of errors],
                "suggested_correction": "corrected citation if needed",
                "source_type": "case/statute/regulation/treaty",
                "jurisdiction": "specific jurisdiction"
            }}
            """
            
            response = self.model.generate_content(prompt)
            result = self._extract_validation_result(response.text, citation)
            return CitationValidationResult(**result)
            
        except Exception as e:
            return CitationValidationResult(
                is_valid=False, 
                error_details=[f"Validation error: {str(e)}"]
            )
    
    def _extract_validation_result(self, text: str, original_citation: str) -> dict:
        """Extract and parse validation result."""
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL | re.MULTILINE)
            if json_match:
                json_text = json_match.group(0)
                json_text = re.sub(r':\s*([^{}\[\],"]+)\s*([,}])', r': "\1"\2', json_text)
                json_text = json_text.replace('\n', '').replace('\r', '')
                json_text = json_text.replace('"is_valid": "false"', '"is_valid": false')
                json_text = json_text.replace('"is_valid": "true"', '"is_valid": true')
                
                parsed_result = json.loads(json_text)
                return {
                    "is_valid": parsed_result.get("is_valid", False),
                    "error_details": parsed_result.get("error_details", []),
                    "suggested_correction": parsed_result.get("suggested_correction", original_citation),
                    "source_type": parsed_result.get("source_type"),
                    "jurisdiction": parsed_result.get("jurisdiction")
                }
        except Exception:
            pass
        
        return {
            "is_valid": False,
            "error_details": ["Unable to parse validation result"],
            "suggested_correction": original_citation
        }

import streamlit as st

class LegalCitationApp:
    def __init__(self):
        st.set_page_config(
            page_title="LegalCite Validator",
            page_icon="⚖️",
            layout="wide"
        )
        
        self.citation_processor = LegalCitationProcessor(
            api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        self.style_options = {
            "Bluebook (US)": CitationStyle.BLUEBOOK_US,
            "OSCOLA": CitationStyle.OSCOLA,
            "Indian Legal": CitationStyle.INDIAN_LEGAL,
        }

    def render_page(self):
        st.title("🏛️ LegalCite Validator")
        st.markdown("Validate legal citations across multiple jurisdictions")
        
        # Citation Style Selection
        selected_style = st.selectbox(
            "Citation Style", 
            list(self.style_options.keys())
        )
        
        # Main Interface
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Input Citation")
            input_citation = st.text_area(
                "Enter your legal citation",
                height=200,
                placeholder="Example (US): Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)"
            )
        
        with col2:
            st.subheader("🔍 Validation Results")
            if st.button("Validate Citation"):
                if input_citation:
                    try:
                        validation_result = self.citation_processor.validate_citation(
                            input_citation, 
                            self.style_options[selected_style]
                        )
                        
                        if validation_result.is_valid:
                            st.success("✅ Citation is Valid")
                        else:
                            st.error("❌ Citation has issues")
                        
                        if validation_result.suggested_correction:
                            st.write("### Suggested Correction")
                            st.info(validation_result.suggested_correction)
                        
                        st.json(validation_result.to_dict())
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

def main():
    app = LegalCitationApp()
    app.render_page()

if __name__ == "__main__":
    main()