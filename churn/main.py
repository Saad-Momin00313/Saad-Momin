import os
import re
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from dataclasses import dataclass, asdict
from enum import Enum, auto
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    QUEENSLAND_STYLE = "Queensland Courts Citation Style"
    FEDERAL_COURT_AU = "Federal Court of Australia Citation Style"
    HIGH_COURT_AU = "High Court of Australia Citation Style"
    
    # Indian Citation Styles
    INDIAN_LEGAL = "Indian Law Institute Citation Style"
    INDIAN_LAW_COMMISSION = "Indian Law Commission Citation Style"
    
    # European Citation Styles
    ECHR = "European Court of Human Rights Citation Style"
    ECJ = "European Court of Justice Citation Style"
    
    # International Citation Styles
    INTERNATIONAL_COURT_JUSTICE = "International Court of Justice Citation Style"
    INTERNATIONAL_CRIMINAL_COURT = "International Criminal Court Citation Style"
    UNCITRAL = "UNCITRAL Citation Style"

class JurisdictionType(Enum):
    # US Jurisdictions
    US_FEDERAL = "us_federal"
    US_STATE = "us_state"
    US_SUPREME_COURT = auto()
    US_FEDERAL_CIRCUIT = auto()
    US_DISTRICT_COURT = auto()
    US_STATE_SUPREME = auto()
    US_STATE_APPELLATE = auto()
    US_BANKRUPTCY = auto()
    
    # UK Jurisdictions
    UK_SUPREME_COURT = auto()
    UK_HIGH_COURT = auto()
    UK_COURT_OF_APPEAL = auto()
    UK_CROWN_COURT = auto()
    
    # Indian Jurisdictions
    INDIAN_SUPREME = auto()
    INDIAN_HIGH_COURT = auto()
    INDIAN_DISTRICT_COURT = auto()
    INDIAN_STATE = "indian_state"
    
    # European Jurisdictions
    EU_COURT_OF_JUSTICE = auto()
    EU_GENERAL_COURT = auto()
    EUROPEAN_COURT_HUMAN_RIGHTS = auto()
    
    # International Jurisdictions
    INTERNATIONAL_COURT_JUSTICE = auto()
    INTERNATIONAL_CRIMINAL_COURT = auto()
    WTO_DISPUTE_PANEL = auto()
    PERMANENT_COURT_ARBITRATION = auto()
    
    # Australian Jurisdictions
    AU_HIGH_COURT = auto()
    AU_FEDERAL_COURT = auto()
    AU_FAMILY_COURT = auto()
    AU_STATE_SUPREME = auto()
    AU_DISTRICT_COURT = auto()
    AU_MAGISTRATES = auto()
    AU_TRIBUNALS = auto()
    AU_STATE = "au_state"  # For state-specific citations

@dataclass
class CitationValidationResult:
    """
    Structured result for citation validation with comprehensive information.
    """
    is_valid: bool
    error_details: list[str] = None
    suggested_correction: Optional[str] = None
    source_type: Optional[str] = None
    jurisdiction: Optional[JurisdictionType] = None

    def to_dict(self):
        """Convert dataclass to dictionary, handling optional fields."""
        return {k: v for k, v in asdict(self).items() if v is not None}

class LegalCitationProcessor:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Legal Citation Processor with robust configuration.
        
        :param api_key: Optional API key for Gemini. 
                        Falls back to environment variable from .env file
        """
        # Secure API key handling
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("No API key provided. Please set GOOGLE_API_KEY in .env file")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini model: {e}")
        
        # Maintain comprehensive citation style metadata
        self._citation_styles = {
            # US Citation Styles
            CitationStyle.BLUEBOOK_US: {
                "full_name": "The Bluebook: A Uniform System of Citation",
                "jurisdiction": [JurisdictionType.US_SUPREME_COURT, JurisdictionType.US_FEDERAL_CIRCUIT]
            },
            CitationStyle.ALWD: {
                "full_name": "ALWD Guide to Legal Citation",
                "jurisdiction": [JurisdictionType.US_FEDERAL, JurisdictionType.US_STATE]
            },
            CitationStyle.CHICAGO_MANUAL_LEGAL: {
                "full_name": "Chicago Manual of Legal Citation",
                "jurisdiction": [JurisdictionType.US_FEDERAL, JurisdictionType.US_STATE]
            },
            
            # UK and Commonwealth Styles
            CitationStyle.OSCOLA: {
                "full_name": "Oxford Standard Citation of Legal Authorities",
                "jurisdiction": [JurisdictionType.UK_SUPREME_COURT, JurisdictionType.UK_HIGH_COURT]
            },
            
            CitationStyle.CANADIAN_GUIDE: {
                "full_name": "Canadian Guide to Uniform Legal Citation",
                "jurisdiction": [JurisdictionType.UK_SUPREME_COURT]
            },
            
            # Indian Citation Styles
            CitationStyle.INDIAN_LEGAL: {
                "full_name": "Indian Law Institute Citation Style",
                "jurisdiction": [JurisdictionType.INDIAN_SUPREME, JurisdictionType.INDIAN_HIGH_COURT]
            },
            CitationStyle.INDIAN_LAW_COMMISSION: {
                "full_name": "Indian Law Commission Citation Style",
                "jurisdiction": [JurisdictionType.INDIAN_SUPREME, JurisdictionType.INDIAN_STATE]
            },
            
            # European Citation Styles
            CitationStyle.ECHR: {
                "full_name": "European Court of Human Rights Citation Style",
                "jurisdiction": [JurisdictionType.EUROPEAN_COURT_HUMAN_RIGHTS]
            },
            CitationStyle.ECJ: {
                "full_name": "European Court of Justice Citation Style",
                "jurisdiction": [JurisdictionType.EU_COURT_OF_JUSTICE, JurisdictionType.EU_GENERAL_COURT]
            },
            
            # International Citation Styles
            CitationStyle.INTERNATIONAL_COURT_JUSTICE: {
                "full_name": "International Court of Justice Citation Style",
                "jurisdiction": [JurisdictionType.INTERNATIONAL_COURT_JUSTICE]
            },
            CitationStyle.INTERNATIONAL_CRIMINAL_COURT: {
                "full_name": "International Criminal Court Citation Style",
                "jurisdiction": [JurisdictionType.INTERNATIONAL_CRIMINAL_COURT]
            },
            CitationStyle.UNCITRAL: {
                "full_name": "UNCITRAL Citation Style",
                "jurisdiction": [JurisdictionType.PERMANENT_COURT_ARBITRATION]
            },
            
            # Australian Citation Styles
            CitationStyle.AGLC: {
                "full_name": "Australian Guide to Legal Citation",
                "jurisdiction": [JurisdictionType.AU_HIGH_COURT, JurisdictionType.AU_FEDERAL_COURT]
            },
            CitationStyle.AUSTLII: {
                "full_name": "AustLII Citation Format",
                "jurisdiction": [JurisdictionType.AU_HIGH_COURT, JurisdictionType.AU_FEDERAL_COURT]
            },
            CitationStyle.QUEENSLAND_STYLE: {
                "full_name": "Queensland Courts Citation Style",
                "jurisdiction": [JurisdictionType.AU_HIGH_COURT, JurisdictionType.AU_FEDERAL_COURT]
            },
            CitationStyle.FEDERAL_COURT_AU: {
                "full_name": "Federal Court of Australia Citation Style",
                "jurisdiction": [JurisdictionType.AU_HIGH_COURT, JurisdictionType.AU_FEDERAL_COURT]
            },
            CitationStyle.HIGH_COURT_AU: {
                "full_name": "High Court of Australia Citation Style",
                "jurisdiction": [JurisdictionType.AU_HIGH_COURT, JurisdictionType.AU_FEDERAL_COURT]
            }
        }
        

    def validate_citation(
        self, 
        citation: str, 
        style: CitationStyle = CitationStyle.BLUEBOOK_US
    ) -> CitationValidationResult:
        """
        Validate legal citations with advanced error handling and AI-powered analysis.
        
        :param citation: The legal citation to validate
        :param style: Citation style to validate against
        :return: Comprehensive validation result
        """
        try:
            style_info = self._citation_styles.get(style, {})
            prompt = f"""
            Strictly Analyze the legal citation '{citation}' according to {style_info.get('full_name', style.value)} rules.
            
            VALIDATION REQUIREMENTS:
            1. Check citation format for {style.value}
            2. Verify all required components are present
            3. Identify any formatting errors
            4. Consider jurisdiction-specific rules for {', '.join(str(j) for j in style_info.get('jurisdiction', []))}
            
            Strictly follow the output JSON format:
            {{
                "is_valid": boolean,
                "error_details": [list of specific errors],
                "suggested_correction": "corrected citation if needed",
                "source_type": "case/statute/regulation/treaty",
                "jurisdiction": "specific jurisdiction from the citation"
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Advanced JSON extraction with multiple fallback strategies
            result = self._extract_validation_result(response.text, citation)
            
            return CitationValidationResult(**result)
        
        except Exception as e:
            return CitationValidationResult(
                is_valid=False, 
                error_details=[f"Unexpected validation error: {str(e)}"]
            )
    
    def _extract_validation_result(self, text: str, original_citation: str) -> dict:
        """
        Robust JSON extraction with multiple parsing strategies.
        
        :param text: Raw AI-generated response text
        :param original_citation: Fallback citation if extraction fails
        :return: Parsed validation result dictionary
        """
        extraction_strategies = [
            self._json_regex_extraction,
            self._manual_parsing_extraction
        ]
        
        for strategy in extraction_strategies:
            result = strategy(text, original_citation)
            if result:
                return result
        
        return {
            "is_valid": False,
            "error_details": ["Unable to parse validation result"],
            "suggested_correction": original_citation
        }
    
    def _json_regex_extraction(self, text: str, original_citation: str) -> Optional[dict]:
        """JSON extraction using regex with comprehensive matching."""
        json_match = re.search(r'\{.*\}', text, re.DOTALL | re.MULTILINE)
        if json_match:
            try:
                # Try to parse JSON, handling potential formatting issues
                json_text = json_match.group(0)
                
                # Clean up common JSON formatting issues
                json_text = re.sub(r':\s*([^{}\[\],"]+)\s*([,}])', r': "\1"\2', json_text)
                json_text = json_text.replace('\n', '').replace('\r', '')
                
                # Ensure is_valid is a boolean
                json_text = json_text.replace('"is_valid": "false"', '"is_valid": false')
                json_text = json_text.replace('"is_valid": "true"', '"is_valid": true')
                
                parsed_result = json.loads(json_text)
                
                # Ensure all expected keys are present
                result = {
                    "is_valid": parsed_result.get("is_valid", False),
                    "error_details": parsed_result.get("error_details", []),
                    "suggested_correction": parsed_result.get("suggested_correction", original_citation),
                    "source_type": parsed_result.get("source_type"),
                    "jurisdiction": parsed_result.get("jurisdiction")
                }
                
                return result
            
            except (json.JSONDecodeError, TypeError) as e:
                # Log the parsing error if needed
                print(f"JSON parsing error: {e}")
                return None
        return None
        
    def _manual_parsing_extraction(self, text: str, original_citation: str) -> Optional[dict]:
        """Fallback manual parsing strategy."""
        try:
            return {
                "is_valid": "error" not in text.lower(),
                "error_details": re.findall(r'error:\s*(.*)', text, re.IGNORECASE),
                "suggested_correction": original_citation
            }
        except Exception:
            return None

    def hyperlink_citation(self, citation: str) -> str:
        """
        Generate intelligent, jurisdiction-aware hyperlinks for citations.
        
        :param citation: Legal citation to hyperlink
        :return: Publicly accessible URL or error message
        """
        try:
            prompt = f"""
            For citation '{citation}':
            1. Identify jurisdiction and court level
            2. Generate direct public hyperlink based on jurisdiction:
               - US: Supreme Court, Google Scholar
               - India: Indian Kanoon, SCC Online
               - UK: BAILII, WestLaw UK
               - EU: EUR-Lex, HUDOC
               - International: ICJ, ICC, WTO databases
            3. Return only the URL, no additional text
            """
            
            response = self.model.generate_content(prompt)
            urls = re.findall(r'https?://\S+', response.text)
            
            return urls[0] if urls else 'No reliable hyperlink found'
        
        except Exception as e:
            return f"Hyperlink generation error: {str(e)}"

import streamlit as st
import traceback
from typing import Dict, Any

class LegalCitationApp:
    def __init__(self):
        """
        Initialize the Streamlit Legal Citation Application
        """
        # Configure Streamlit page
        st.set_page_config(
            page_title="LegalCite: AI Citation Assistant",
            page_icon="⚖️",
            layout="wide"
        )
        
        # Initialize citation processor with API key from .env
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            st.error("Please set GOOGLE_API_KEY in your .env file")
            st.stop()
            
        self.citation_processor = LegalCitationProcessor(api_key=api_key)
        
        # Citation styles grouped by region
        self.style_options = {
            # US Citation Styles
            "US-Bluebook": CitationStyle.BLUEBOOK_US,
            "US-ALWD Guide": CitationStyle.ALWD,
            "US-Chicago Manual": CitationStyle.CHICAGO_MANUAL_LEGAL,
            
            # UK and Commonwealth Styles
            "UK-OSCOLA": CitationStyle.OSCOLA,
            "UK-Canadian Guide": CitationStyle.CANADIAN_GUIDE,
            
            # Indian Citation Styles
            "Indian Legal": CitationStyle.INDIAN_LEGAL,
            "Indian Law Commission": CitationStyle.INDIAN_LAW_COMMISSION,
            
            # European Citation Styles
            "EU-ECHR": CitationStyle.ECHR,
            "EU-ECJ": CitationStyle.ECJ,
            
            # International Citation Styles
            "INT-Court of Justice": CitationStyle.INTERNATIONAL_COURT_JUSTICE,
            "INT-Criminal Court": CitationStyle.INTERNATIONAL_CRIMINAL_COURT,
            "INT-UNCITRAL": CitationStyle.UNCITRAL,
            
            # Australian Citation Styles
            "AUS-AGLC": CitationStyle.AGLC,
            "AUS-AustLII": CitationStyle.AUSTLII,
            "AUS-Queensland": CitationStyle.QUEENSLAND_STYLE,
            "AUS-Federal Court": CitationStyle.FEDERAL_COURT_AU,
            "AUS-High Court": CitationStyle.HIGH_COURT_AU,
        }
        
        # Jurisdiction mapping by region
        self.jurisdictions = {
            "US": ["Federal Courts", "State Courts", "Supreme Court", "Federal Circuit", "District Courts"],
            "UK": ["Supreme Court", "High Court", "Court of Appeal", "Crown Court"],
            "India": ["Supreme Court", "High Courts", "District Courts"],
            "EU": ["Court of Justice", "General Court", "Court of Human Rights"],
            "International": ["ICJ", "ICC", "WTO", "Arbitration Court"],
            "Australia": ["High Court", "Federal Court", "Family Court", "State Courts", "Tribunals"]
        }

    def render_page(self):
        """
        Main Streamlit page rendering method
        """
        # Page Title and Introduction
        st.title("🏛️ LegalCite: AI-Powered Citation Assistant")
        st.markdown("""
        An intelligent tool for validating and analyzing legal citations across 
        major legal systems.
        """)
        
        # Sidebar Configuration
        self._render_sidebar()
        
        # Main Content
        self._render_validation_interface()

    def _render_sidebar(self):
        """Render configuration sidebar with dynamic jurisdiction filtering"""
        with st.sidebar:
            st.header("🔧 Configuration")
            
            # Citation Style Selection
            self.selected_style = st.selectbox(
                "Preferred Citation Style", 
                list(self.style_options.keys())
            )
            
            # Get relevant jurisdictions based on selected style
            region = self._get_region_from_style(self.selected_style)
            jurisdictions = self.jurisdictions.get(region, [])
            
            # Jurisdiction Selection
            self.selected_jurisdiction = st.selectbox(
                "Jurisdiction", 
                jurisdictions
            )
            
            # Additional Sidebar Information
            st.info("""
            💡 Pro Tips:
            - Use full, precise citations
            - Check formatting carefully
            - Different jurisdictions have unique rules
            """)

    def _get_region_from_style(self, style_name: str) -> str:
        """Get region from style name prefix"""
        if style_name.startswith("US-"):
            return "US"
        elif style_name.startswith("UK-"):
            return "UK"
        elif style_name.startswith("Indian"):
            return "India"
        elif style_name.startswith("EU-"):
            return "EU"
        elif style_name.startswith("INT-"):
            return "International"
        elif style_name.startswith("AUS-"):
            return "Australia"
        return "International"  # fallback

    def _render_validation_interface(self):
        """Render the citation validation interface"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Input Citation")
            input_citation = st.text_area(
                "Paste your legal citation", 
                height=200
            )
        
        with col2:
            st.subheader("🔍 Citation Analysis")
            if st.button("Analyze Citation"):
                if input_citation:
                    try:
                        # Validate Citation
                        validation_result = self.citation_processor.validate_citation(
                            input_citation, 
                            self.style_options[self.selected_style]
                        )
                        
                        # Display Validation Results
                        st.write("### Validation Results")
                        
                        # Validity Indicator
                        if validation_result.is_valid:
                            st.success("✅ Citation is Valid")
                        else:
                            st.error("❌ Citation has issues")
                        
                        # Detailed Results
                        result_dict = validation_result.to_dict()
                        
                        # Add suggested correction if available
                        if validation_result.suggested_correction:
                            st.write("### Suggested Correction")
                            st.info(validation_result.suggested_correction)
                        
                        st.json(result_dict)
                        
                        # Hyperlink (if valid)
                        if validation_result.is_valid:
                            hyperlink = self.citation_processor.hyperlink_citation(input_citation)
                            st.markdown(f"### 🔗 Hyperlink\n[Access Full Text]({hyperlink})")

                    except Exception as e:
                        st.error(f"Error processing citation: {str(e)}")
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())

def main():
    """Main application entry point"""
    app = LegalCitationApp()
    app.render_page()

if __name__ == "__main__":
    main()