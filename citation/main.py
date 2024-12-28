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
                        Falls back to environment variable or raises an error.
        """
        # Secure API key handling
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("No API key provided. Set GOOGLE_API_KEY environment variable.")
        
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

    def reformat_citation(
        self, 
        citation: str, 
        source_style: CitationStyle,
        target_style: CitationStyle
    ) -> str:
        """
        Intelligently reformat citations between different styles.
        
        :param citation: Original citation
        :param source_style: Current citation style
        :param target_style: Desired target citation style
        :return: Reformatted citation
        """
        try:
            prompt = f"""
            Precisely reformat citation '{citation}' from {source_style.value} to {target_style.value}:
            - Preserve source integrity
            - Apply {target_style.value} formatting rules
            - Maintain all critical case information
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
        
        except Exception as e:
            return f"Citation reformatting error: {str(e)}"

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
        
        # Initialize citation processor
        self.citation_processor = LegalCitationProcessor(
            api_key=os.getenv('GOOGLE_API_KEY')
        )
        
        # Updated style options to include all citation styles
        self.style_options = {
            # US Citation Styles
            "US-Bluebook (US)": CitationStyle.BLUEBOOK_US,
            "US-ALWD Guide": CitationStyle.ALWD,
            "US-Chicago Manual Legal": CitationStyle.CHICAGO_MANUAL_LEGAL,
            
            # UK and Commonwealth Styles
            "OSCOLA": CitationStyle.OSCOLA,
            "Australian Guide (AGLC)": CitationStyle.AGLC,
            "Canadian Guide (McGill)": CitationStyle.CANADIAN_GUIDE,
            
            # Indian Citation Styles
            "Indian Legal": CitationStyle.INDIAN_LEGAL,
            "Indian Law Commission": CitationStyle.INDIAN_LAW_COMMISSION,
            
            # European Citation Styles
            "EUR-ECHR Style": CitationStyle.ECHR,
            "EUR-ECJ Style": CitationStyle.ECJ,
            
            # International Citation Styles
            "INT-ICJ Style": CitationStyle.INTERNATIONAL_COURT_JUSTICE,
            "INT-ICC Style": CitationStyle.INTERNATIONAL_CRIMINAL_COURT,
            "INT-UNCITRAL": CitationStyle.UNCITRAL,
            
            # Australian Citation Styles
            "AUS-AGLC": CitationStyle.AGLC,
            "AUS-AustLII": CitationStyle.AUSTLII,
            "AUS-Queensland Courts": CitationStyle.QUEENSLAND_STYLE,
            "AUS-Federal Court": CitationStyle.FEDERAL_COURT_AU,
            "AUS-High Court": CitationStyle.HIGH_COURT_AU,
        }
        
        # Updated jurisdiction options to include all jurisdictions
        self.jurisdiction_options = {
            # US Jurisdictions
            "US Federal": JurisdictionType.US_FEDERAL,
            "US State": JurisdictionType.US_STATE,
            "US Supreme Court": JurisdictionType.US_SUPREME_COURT,
            "US Federal Circuit": JurisdictionType.US_FEDERAL_CIRCUIT,
            "US District Court": JurisdictionType.US_DISTRICT_COURT,
            "US State Supreme": JurisdictionType.US_STATE_SUPREME,
            "US State Appellate": JurisdictionType.US_STATE_APPELLATE,
            "US Bankruptcy": JurisdictionType.US_BANKRUPTCY,
            
            # UK Jurisdictions
            "UK Supreme Court": JurisdictionType.UK_SUPREME_COURT,
            "UK High Court": JurisdictionType.UK_HIGH_COURT,
            "UK Court of Appeal": JurisdictionType.UK_COURT_OF_APPEAL,
            "UK Crown Court": JurisdictionType.UK_CROWN_COURT,
            
            # Indian Jurisdictions
            "Indian Supreme Court": JurisdictionType.INDIAN_SUPREME,
            "Indian High Court": JurisdictionType.INDIAN_HIGH_COURT,
            "Indian District Court": JurisdictionType.INDIAN_DISTRICT_COURT,
            "Indian State": JurisdictionType.INDIAN_STATE,
            
            # European Jurisdictions
            "EU Court of Justice": JurisdictionType.EU_COURT_OF_JUSTICE,
            "EU General Court": JurisdictionType.EU_GENERAL_COURT,
            "European Court of Human Rights": JurisdictionType.EUROPEAN_COURT_HUMAN_RIGHTS,
            
            # International Jurisdictions
            "International Court of Justice": JurisdictionType.INTERNATIONAL_COURT_JUSTICE,
            "International Criminal Court": JurisdictionType.INTERNATIONAL_CRIMINAL_COURT,
            "WTO Dispute Panel": JurisdictionType.WTO_DISPUTE_PANEL,
            "Permanent Court of Arbitration": JurisdictionType.PERMANENT_COURT_ARBITRATION,
            
            # Australian Jurisdictions
            "High Court of Australia": JurisdictionType.AU_HIGH_COURT,
            "Federal Court of Australia": JurisdictionType.AU_FEDERAL_COURT,
            "Family Court of Australia": JurisdictionType.AU_FAMILY_COURT,
            "State Supreme Courts": JurisdictionType.AU_STATE_SUPREME,
            "District Courts": JurisdictionType.AU_DISTRICT_COURT,
            "Magistrates Courts": JurisdictionType.AU_MAGISTRATES,
            "Australian Tribunals": JurisdictionType.AU_TRIBUNALS,
            "Australian State": JurisdictionType.AU_STATE,
        }

    def render_page(self):
        """
        Main Streamlit page rendering method
        """
        # Page Title and Introduction
        st.title("🏛️ LegalCite: AI-Powered Citation Assistant")
        st.markdown("""
        An intelligent tool for validating, reformatting, and analyzing 
        legal citations Major legal systems.
        """)
        
        # Sidebar Configuration
        self._render_sidebar()
        
        # Main Content Tabs
        tab1, tab2, tab3 = st.tabs([
            "Citation Validation", 
            "Citation Reformatting", 
            "Citation Resources"
        ])
        
        with tab1:
            self._render_validation_tab()
        
        with tab2:
            self._render_reformatting_tab()
        
        with tab3:
            self._render_resources_tab()

    def _render_sidebar(self):
        """Render configuration sidebar with dynamic jurisdiction filtering"""
        with st.sidebar:
            st.header("🔧 Configuration")
            
            # Citation Style Selection
            self.selected_style = st.selectbox(
                "Preferred Citation Style", 
                list(self.style_options.keys())
            )
            
            # Get the selected CitationStyle enum
            selected_style_enum = self.style_options[self.selected_style]
            
            # Get relevant jurisdictions for the selected style
            relevant_jurisdictions = self._get_relevant_jurisdictions(selected_style_enum)
            
            # Filtered Jurisdiction Selection
            self.selected_jurisdiction = st.selectbox(
                "Jurisdiction", 
                list(relevant_jurisdictions.keys())
            )
            
            # Additional Sidebar Information
            st.info("""
            💡 Pro Tips:
            - Use full, precise citations
            - Check formatting carefully
            - Different jurisdictions have unique rules
            """)

    def _get_relevant_jurisdictions(self, style: CitationStyle) -> Dict[str, JurisdictionType]:
        """Get jurisdictions relevant to the selected citation style"""
        filtered_jurisdictions = {}
        
        # Match citation style with relevant jurisdictions
        if style == CitationStyle.INDIAN_LEGAL or style == CitationStyle.INDIAN_LAW_COMMISSION:
            # Indian Citation Styles
            for name, jtype in self.jurisdiction_options.items():
                if name.startswith("Indian"):
                    filtered_jurisdictions[name] = jtype
        
        elif style in [CitationStyle.BLUEBOOK_US, CitationStyle.ALWD, CitationStyle.CHICAGO_MANUAL_LEGAL]:
            # US Citation Styles
            for name, jtype in self.jurisdiction_options.items():
                if name.startswith("US"):
                    filtered_jurisdictions[name] = jtype
        
        elif style in [CitationStyle.OSCOLA, CitationStyle.AGLC, CitationStyle.CANADIAN_GUIDE]:
            # UK and Commonwealth Styles
            for name, jtype in self.jurisdiction_options.items():
                if name.startswith("UK"):
                    filtered_jurisdictions[name] = jtype
        
        elif style in [CitationStyle.ECHR, CitationStyle.ECJ]:
            # European Citation Styles
            for name, jtype in self.jurisdiction_options.items():
                if name.startswith("EU") or name.startswith("European"):
                    filtered_jurisdictions[name] = jtype
        
        elif style in [CitationStyle.INTERNATIONAL_COURT_JUSTICE, 
                      CitationStyle.INTERNATIONAL_CRIMINAL_COURT, 
                      CitationStyle.UNCITRAL]:
            # International Citation Styles
            for name, jtype in self.jurisdiction_options.items():
                if (name.startswith("International") or 
                    name.startswith("WTO") or 
                    name.startswith("Permanent")):
                    filtered_jurisdictions[name] = jtype
        
        elif style in [CitationStyle.AGLC, CitationStyle.AUSTLII, 
                      CitationStyle.QUEENSLAND_STYLE, CitationStyle.FEDERAL_COURT_AU, 
                      CitationStyle.HIGH_COURT_AU]:
            # Australian Citation Styles
            relevant_jurisdiction_types = ["STATE", "TERRITORY"]  # Define the types you want to include
            for name, jtype in self.jurisdiction_options.items():
                if name.startswith("AU") or jtype in relevant_jurisdiction_types:
                    filtered_jurisdictions[name] = jtype
        
        else:
            # Fallback: show all jurisdictions if style not recognized
            filtered_jurisdictions = self.jurisdiction_options
        
        return filtered_jurisdictions

    def _render_validation_tab(self):
        """Render the citation validation interface"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 Input Citation")
            input_citation = st.text_area(
                "Paste your legal citation", 
                height=200,
                placeholder="Example (US): Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)\nExample (India): AIR 1973 SC 1461"
            )
        
        with col2:
            st.subheader("🔍 Citation Analysis")
            if st.button("Analyze Citation"):
                if input_citation:
                    try:
                        # Validate Citation
                        validation_result = self._validate_citation(
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
                            hyperlink = self._get_hyperlink(input_citation)
                            st.markdown(f"### 🔗 Hyperlink\n[Access Full Text]({hyperlink})")
                    
                    except Exception as e:
                        st.error(f"Error processing citation: {str(e)}")
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())

    def _render_reformatting_tab(self):
        """Render the citation reformatting interface"""
        st.subheader("🔄 Citation Reformatting")
        
        col1, col2 = st.columns(2)
        
        with col1:
            source_style = st.selectbox(
                "Source Citation Style", 
                list(self.style_options.keys())
            )
        
        with col2:
            target_style = st.selectbox(
                "Target Citation Style", 
                list(self.style_options.keys())
            )
        
        input_citation = st.text_area(
            "Citation to Reformat",
            placeholder="Enter full legal citation here"
        )
        
        if st.button("Reformat Citation"):
            try:
                reformatted = self._reformat_citation(
                    input_citation, 
                    self.style_options[source_style], 
                    self.style_options[target_style]
                )
                st.success("Reformatted Citation:")
                st.code(reformatted)
            except Exception as e:
                st.error(f"Reformatting error: {str(e)}")

    def _render_resources_tab(self):
        """Render educational resources and additional information"""
        st.subheader("📚 Legal Citation Resources")
        
        resources = [
            {
                "name": "The Bluebook",
                "description": "Comprehensive US legal citation guide",
                "link": "https://guides.library.duke.edu/bluebook"
            },
            {
                "name": "Indian Legal Citation Manual",
                "description": "Authoritative guide for Indian legal citations",
                "link": "https://www.advocatekhoj.com/resources/citation/"
            },
            {
                "name": "AGLC Guide",
                "description": "Australian Guide to Legal Citation (4th Edition)",
                "link": "https://law.unimelb.edu.au/mulr/aglc/about"
            },
            {
                "name": "AustLII Citation Guide",
                "description": "AustLII's Guide to Legal Citation",
                "link": "http://www.austlii.edu.au/techlib/standards/cite.html"
            },
            {
                "name": "Federal Court Citation Guide",
                "description": "Federal Court of Australia Citation Guide",
                "link": "https://www.fedcourt.gov.au/digital-law-library/citation-guide"
            }
        ]
        
        for resource in resources:
            st.markdown(f"""
            ### {resource['name']}
            {resource['description']}
            [Learn More]({resource['link']})
            """)

    def _validate_citation(self, citation: str, style: CitationStyle):
        """Wrapper for citation validation with additional error handling"""
        return self.citation_processor.validate_citation(citation, style)

    def _get_hyperlink(self, citation: str) -> str:
        """Wrapper for hyperlink generation"""
        return self.citation_processor.hyperlink_citation(citation)

    def _reformat_citation(
        self, 
        citation: str, 
        source_style: CitationStyle, 
        target_style: CitationStyle
    ) -> str:
        """Wrapper for citation reformatting"""
        return self.citation_processor.reformat_citation(
            citation, source_style, target_style
        )

def main():
    """Main application entry point"""
    app = LegalCitationApp()
    app.render_page()

if __name__ == "__main__":
    main()