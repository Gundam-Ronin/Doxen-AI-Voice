"""
Phase 7.1 - Domain-Specific Vocabulary Loader
Loads industry-specific terms for better speech recognition and understanding.
"""

from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass


@dataclass
class IndustryVocabulary:
    industry: str
    technical_terms: List[str]
    common_services: List[str]
    equipment_names: List[str]
    problem_descriptions: List[str]
    brands: List[str]
    emergency_terms: List[str]
    pricing_terms: List[str]


class VocabularyLoader:
    """Loads and manages industry-specific vocabulary for AI understanding."""
    
    def __init__(self):
        self.vocabularies: Dict[str, IndustryVocabulary] = {}
        self._load_default_vocabularies()
    
    def _load_default_vocabularies(self):
        """Load built-in industry vocabularies."""
        
        self.vocabularies["hvac"] = IndustryVocabulary(
            industry="hvac",
            technical_terms=[
                "HVAC", "AC", "air conditioning", "furnace", "heat pump", "ductwork",
                "compressor", "condenser", "evaporator", "refrigerant", "freon", "R-410A",
                "thermostat", "capacitor", "blower motor", "air handler", "coil",
                "BTU", "SEER rating", "tonnage", "CFM", "static pressure",
                "mini split", "ductless", "zone system", "damper", "plenum",
                "return air", "supply air", "diffuser", "register", "grille"
            ],
            common_services=[
                "AC repair", "AC installation", "heating repair", "furnace tune-up",
                "duct cleaning", "refrigerant recharge", "thermostat installation",
                "emergency AC repair", "heat pump service", "indoor air quality",
                "preventive maintenance", "seasonal tune-up", "system replacement"
            ],
            equipment_names=[
                "Carrier", "Trane", "Lennox", "Rheem", "Goodman", "Bryant", "York",
                "Daikin", "Mitsubishi", "Fujitsu", "American Standard", "Ruud",
                "Amana", "Heil", "Tempstar", "Comfortmaker", "Nest", "Ecobee", "Honeywell"
            ],
            problem_descriptions=[
                "not cooling", "not heating", "blowing warm air", "blowing cold air",
                "making noise", "strange smell", "short cycling", "won't turn on",
                "freezing up", "leaking water", "high energy bills", "uneven temperatures",
                "humidity issues", "poor airflow", "thermostat not working"
            ],
            brands=[
                "Carrier", "Trane", "Lennox", "Rheem", "Goodman", "Bryant", "York"
            ],
            emergency_terms=[
                "no heat", "no AC", "carbon monoxide", "gas smell", "burning smell",
                "frozen pipes", "system won't start", "sparking", "smoke"
            ],
            pricing_terms=[
                "service call fee", "diagnostic fee", "tune-up", "estimate",
                "flat rate", "hourly rate", "parts and labor", "warranty"
            ]
        )
        
        self.vocabularies["plumbing"] = IndustryVocabulary(
            industry="plumbing",
            technical_terms=[
                "pipe", "drain", "faucet", "toilet", "water heater", "sump pump",
                "garbage disposal", "shut-off valve", "P-trap", "S-trap", "clean-out",
                "main line", "sewer line", "septic tank", "backflow preventer",
                "pressure regulator", "expansion tank", "anode rod", "flex line",
                "PVC", "copper", "PEX", "cast iron", "galvanized"
            ],
            common_services=[
                "drain cleaning", "leak repair", "toilet repair", "faucet replacement",
                "water heater installation", "sewer line repair", "hydro jetting",
                "camera inspection", "repiping", "slab leak repair", "gas line repair",
                "fixture installation", "water softener installation"
            ],
            equipment_names=[
                "Kohler", "Moen", "Delta", "American Standard", "Rheem", "AO Smith",
                "Bradford White", "Rinnai", "Navien", "InSinkErator", "Watts"
            ],
            problem_descriptions=[
                "clogged drain", "leaking pipe", "dripping faucet", "running toilet",
                "no hot water", "low water pressure", "slow drain", "gurgling",
                "sewage smell", "water stain", "water damage", "frozen pipes",
                "burst pipe", "backed up", "overflowing"
            ],
            brands=[
                "Kohler", "Moen", "Delta", "Rheem", "AO Smith"
            ],
            emergency_terms=[
                "burst pipe", "flooding", "sewage backup", "no water", "gas leak",
                "water main break", "overflowing toilet", "major leak"
            ],
            pricing_terms=[
                "service call", "diagnostic", "camera inspection fee", "hydro jetting cost",
                "flat rate", "hourly rate", "parts and labor"
            ]
        )
        
        self.vocabularies["electrical"] = IndustryVocabulary(
            industry="electrical",
            technical_terms=[
                "circuit breaker", "fuse box", "panel", "outlet", "switch", "wiring",
                "voltage", "amperage", "ground", "GFCI", "AFCI", "surge protector",
                "junction box", "conduit", "romex", "wire gauge", "three-way switch",
                "dimmer", "ceiling fan", "recessed lighting", "track lighting"
            ],
            common_services=[
                "panel upgrade", "outlet installation", "circuit breaker replacement",
                "wiring repair", "lighting installation", "ceiling fan installation",
                "GFCI installation", "whole house surge protection", "electrical inspection",
                "generator installation", "EV charger installation", "rewiring"
            ],
            equipment_names=[
                "Square D", "Eaton", "Siemens", "GE", "Leviton", "Lutron",
                "Generac", "Kohler", "Briggs & Stratton", "ChargePoint", "Tesla"
            ],
            problem_descriptions=[
                "tripping breaker", "flickering lights", "outlet not working",
                "burning smell", "sparking outlet", "power outage", "buzzing sound",
                "warm outlet", "dead outlet", "dimming lights", "shock", "no power"
            ],
            brands=[
                "Square D", "Eaton", "Siemens", "GE", "Leviton"
            ],
            emergency_terms=[
                "electrical fire", "sparking", "burning smell", "shock", "power outage",
                "exposed wires", "smoking outlet", "no power"
            ],
            pricing_terms=[
                "service call", "diagnostic fee", "permit fees", "code compliance",
                "hourly rate", "flat rate"
            ]
        )
        
        self.vocabularies["cleaning"] = IndustryVocabulary(
            industry="cleaning",
            technical_terms=[
                "deep clean", "standard clean", "move-in clean", "move-out clean",
                "sanitization", "disinfection", "steam cleaning", "pressure washing",
                "carpet cleaning", "upholstery cleaning", "grout cleaning"
            ],
            common_services=[
                "house cleaning", "office cleaning", "deep cleaning", "move-out cleaning",
                "post-construction cleaning", "window cleaning", "carpet cleaning",
                "floor polishing", "recurring cleaning", "one-time cleaning"
            ],
            equipment_names=[
                "Dyson", "Miele", "Shark", "Bissell", "Hoover", "Karcher"
            ],
            problem_descriptions=[
                "stains", "odors", "pet mess", "mold", "mildew", "dust buildup",
                "grime", "grease", "hard water stains", "soap scum"
            ],
            brands=[],
            emergency_terms=[
                "flood cleanup", "biohazard", "mold remediation", "hoarding cleanup"
            ],
            pricing_terms=[
                "hourly rate", "flat rate", "per room", "per square foot",
                "recurring discount", "add-on services"
            ]
        )
        
        self.vocabularies["pest_control"] = IndustryVocabulary(
            industry="pest_control",
            technical_terms=[
                "infestation", "extermination", "fumigation", "bait station",
                "treatment", "inspection", "barrier treatment", "spot treatment",
                "colony", "nest", "harborage"
            ],
            common_services=[
                "pest inspection", "ant treatment", "roach treatment", "termite inspection",
                "bed bug treatment", "rodent control", "mosquito treatment",
                "wildlife removal", "preventive treatment", "quarterly service"
            ],
            equipment_names=[
                "Terminix", "Orkin", "Rentokil", "Ehrlich", "Western Pest"
            ],
            problem_descriptions=[
                "ants", "roaches", "cockroaches", "termites", "bed bugs", "mice", "rats",
                "spiders", "wasps", "bees", "mosquitoes", "fleas", "ticks",
                "droppings", "damage", "bites", "nests"
            ],
            brands=[],
            emergency_terms=[
                "bee swarm", "wasp nest", "snake", "wildlife intrusion",
                "severe infestation", "aggressive pest"
            ],
            pricing_terms=[
                "inspection fee", "treatment cost", "quarterly plan", "annual plan",
                "per treatment", "warranty"
            ]
        )
        
        self.vocabularies["general"] = IndustryVocabulary(
            industry="general",
            technical_terms=[
                "repair", "installation", "replacement", "maintenance", "service",
                "inspection", "estimate", "quote"
            ],
            common_services=[
                "repair service", "installation", "maintenance", "emergency service",
                "inspection", "estimate"
            ],
            equipment_names=[],
            problem_descriptions=[
                "not working", "broken", "leaking", "making noise", "won't start",
                "needs repair", "needs replacement"
            ],
            brands=[],
            emergency_terms=[
                "emergency", "urgent", "immediately", "right away", "ASAP"
            ],
            pricing_terms=[
                "cost", "price", "estimate", "quote", "fee", "rate"
            ]
        )
    
    def get_vocabulary(self, industry: str) -> IndustryVocabulary:
        """Get vocabulary for a specific industry."""
        industry_lower = industry.lower()
        return self.vocabularies.get(industry_lower, self.vocabularies["general"])
    
    def get_all_terms(self, industry: str) -> Set[str]:
        """Get all vocabulary terms for an industry."""
        vocab = self.get_vocabulary(industry)
        all_terms = set()
        all_terms.update(vocab.technical_terms)
        all_terms.update(vocab.common_services)
        all_terms.update(vocab.equipment_names)
        all_terms.update(vocab.problem_descriptions)
        all_terms.update(vocab.brands)
        all_terms.update(vocab.emergency_terms)
        all_terms.update(vocab.pricing_terms)
        return all_terms
    
    def match_service(self, text: str, industry: str) -> Optional[str]:
        """Match text to a known service."""
        vocab = self.get_vocabulary(industry)
        text_lower = text.lower()
        
        for service in vocab.common_services:
            if service.lower() in text_lower:
                return service
        
        return None
    
    def match_problem(self, text: str, industry: str) -> Optional[str]:
        """Match text to a known problem description."""
        vocab = self.get_vocabulary(industry)
        text_lower = text.lower()
        
        for problem in vocab.problem_descriptions:
            if problem.lower() in text_lower:
                return problem
        
        return None
    
    def is_emergency(self, text: str, industry: str) -> bool:
        """Check if text contains emergency terms."""
        vocab = self.get_vocabulary(industry)
        text_lower = text.lower()
        
        for term in vocab.emergency_terms:
            if term.lower() in text_lower:
                return True
        
        return False
    
    def get_speech_hints(self, industry: str) -> List[str]:
        """Get speech recognition hints for better accuracy."""
        vocab = self.get_vocabulary(industry)
        
        hints = []
        hints.extend(vocab.technical_terms[:20])
        hints.extend(vocab.common_services[:10])
        hints.extend(vocab.equipment_names[:10])
        hints.extend(vocab.brands[:5])
        
        return hints
    
    def enhance_system_prompt(self, base_prompt: str, industry: str) -> str:
        """Enhance system prompt with industry vocabulary."""
        vocab = self.get_vocabulary(industry)
        
        services_str = ", ".join(vocab.common_services[:8])
        problems_str = ", ".join(vocab.problem_descriptions[:8])
        emergency_str = ", ".join(vocab.emergency_terms[:5])
        
        enhancement = f"""

INDUSTRY-SPECIFIC KNOWLEDGE ({industry.upper()}):
- Common services: {services_str}
- Common problems customers describe: {problems_str}
- Emergency situations to prioritize: {emergency_str}

When customers mention these specific terms, acknowledge them properly and respond with expertise."""
        
        return base_prompt + enhancement
    
    def add_custom_vocabulary(
        self,
        industry: str,
        terms: Dict[str, List[str]]
    ):
        """Add custom vocabulary for a business."""
        if industry not in self.vocabularies:
            self.vocabularies[industry] = IndustryVocabulary(
                industry=industry,
                technical_terms=[],
                common_services=[],
                equipment_names=[],
                problem_descriptions=[],
                brands=[],
                emergency_terms=[],
                pricing_terms=[]
            )
        
        vocab = self.vocabularies[industry]
        
        if terms.get("technical_terms"):
            vocab.technical_terms.extend(terms["technical_terms"])
        if terms.get("services"):
            vocab.common_services.extend(terms["services"])
        if terms.get("equipment"):
            vocab.equipment_names.extend(terms["equipment"])
        if terms.get("problems"):
            vocab.problem_descriptions.extend(terms["problems"])
        if terms.get("brands"):
            vocab.brands.extend(terms["brands"])
        if terms.get("emergencies"):
            vocab.emergency_terms.extend(terms["emergencies"])


vocabulary_loader = VocabularyLoader()
