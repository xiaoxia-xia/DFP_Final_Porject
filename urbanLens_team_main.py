#!/usr/bin/env python3
import pandas as pd
import os
from src.scrapers.scrape_levels import scrape_levels_main
from src.pipelines.fbi_crime_pipeline import fbi_crime_pipeline_main
from src.pipelines.zillow_to_rent_data import zillow_to_rent_main
import asyncio
import sys, subprocess

class CityAffordabilityAnalyzer:
    def __init__(self):
        # Initialize dataframes
        self.rent_data = None
        self.crime_data = None
        self.salary_data = {}
        
        # Job mapping
        self.job_mapping = {
            '1': 'Web Developer',
            '2': 'Machine Learning Engineer', 
            '3': 'Data Engineer',
            '4': 'Full-Stack Software Engineer',
            '5': 'Analytics Product Manager',
        }
        
        # State abbreviation mapping
        self.state_abbrev = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'
        }
        # Inverse map for convenience
        self.full_to_abbr = {v:k for k,v in self.state_abbrev.items()}
    
    def _normalize_rent_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        # Try to find columns regardless of exact names
        city_col = cols.get('regionname') or cols.get('city')
        state_col = cols.get('state') or cols.get('statecode') or cols.get('state_abbrev')
        # Rent may be 'avg_2024', 'avg_rent', or similar
        rent_col = None
        for key in ['avg_2024', 'avg_rent', 'rent', 'average_rent']:
            if key in cols:
                rent_col = cols[key]
                break
        if not city_col or not state_col or not rent_col:
            raise ValueError(f"Unexpected columns in rent data: {df.columns.tolist()}")
        out = df.rename(columns={city_col: 'RegionName', state_col: 'State', rent_col: 'avg_2024'}).copy()
        # Force state abbreviations if they look like full names
        out['State'] = out['State'].apply(lambda s: self.full_to_abbr.get(str(s), str(s))).str.upper()
        return out[['RegionName','State','avg_2024']]
    
    def _normalize_crime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # Accept either 'state' (abbr) or 'State' (full) and 'composite_score'
        cols = {c.lower(): c for c in df.columns}
        score_col = cols.get('composite_score') or cols.get('composite') or cols.get('score')
        if not score_col:
            raise ValueError(f"Unexpected columns in crime data: {df.columns.tolist()}")
        # Determine state form
        if 'state' in cols and cols['state'] != score_col:
            state_col = cols['state']
            out = df.rename(columns={state_col: 'state', score_col: 'composite_score'}).copy()
            # If values look like full names, convert to abbr
            sample = str(out['state'].iloc[0])
            if len(sample) > 2:  # likely full name
                out['state'] = out['state'].map(lambda s: self.full_to_abbr.get(str(s), str(s))).str.upper()
            else:
                out['state'] = out['state'].str.upper()
            return out[['state','composite_score']]
        elif 'state' not in cols and 'state_name' not in cols and 'statefull' not in cols and 'State' in df.columns:
            # Handle file with 'State' full name
            out = df.rename(columns={'State': 'state', score_col: 'composite_score'}).copy()
            out['state'] = out['state'].map(lambda s: self.full_to_abbr.get(str(s), str(s))).str.upper()
            return out[['state','composite_score']]
        else:
            # Try any column that contains 'state' token
            state_like = [c for c in df.columns if 'state' in c.lower()]
            if not state_like:
                raise ValueError(f"No state column in crime data: {df.columns.tolist()}")
            state_col = state_like[0]
            out = df.rename(columns={state_col: 'state', score_col: 'composite_score'}).copy()
            out['state'] = out['state'].map(lambda s: self.full_to_abbr.get(str(s), str(s))).str.upper()
            return out[['state','composite_score']]
    
    def _normalize_salary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        city_col = cols.get('city')
        sal_col = cols.get('salary') or cols.get('avg_salary') or cols.get('average_salary')
        if not city_col or not sal_col:
            raise ValueError(f"Unexpected columns in salary data: {df.columns.tolist()}")
        out = df.rename(columns={city_col:'City', sal_col:'Salary'}).copy()
        return out[['City','Salary']]
    
    def load_data(self):
        """Load all data files"""
        try:
            # Base dir (project root where this script is) and data directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, 'data')
            print(f"Debug: script base dir = {base_dir}")
            print(f"Debug: data dir = {data_dir}")

            # Ensure data directory exists
            if not os.path.isdir(data_dir):
                print(f"⚠ Error: data directory not found: {data_dir}")
                return False

            # Load rent data
            rent_path = os.path.join(data_dir, 'rent_data.csv')
            if not os.path.exists(rent_path):
                print(f"⚠ Error: rent data file not found at {rent_path}")
                return False
            rent_raw = pd.read_csv(rent_path)
            self.rent_data = self._normalize_rent_columns(rent_raw)
            print(f"✓ Rent data loaded successfully ({rent_path})")

            # Load crime data
            crime_path = os.path.join(data_dir, 'crime_data.csv')
            if not os.path.exists(crime_path):
                print(f"⚠ Error: crime data file not found at {crime_path}")
                return False
            crime_raw = pd.read_csv(crime_path)
            self.crime_data = self._normalize_crime_columns(crime_raw)
            print(f"✓ Crime data loaded successfully ({crime_path})")

            # Load salary data for each job title
            salary_files = {
                "Web Developer": "web_developer_salary.csv",
                "Machine Learning Engineer": "machine_learning_engineer_salary.csv",
                "Data Engineer":  "data_engineer_salary.csv",
                "Full-Stack Software Engineer": "full_stack_software_engineer_salary.csv",
                "Analytics Product Manager": "analytics_product_manager_salary.csv",
            }

            missing_salary_files = []
            for job, filename in salary_files.items():
                filepath = os.path.join(data_dir, filename)
                if os.path.exists(filepath):
                    try:
                        df = pd.read_csv(filepath)
                        self.salary_data[job] = self._normalize_salary_columns(df)
                        print(f"✓ {job} salary data loaded successfully ({filepath})")
                    except Exception as e:
                        print(f"⚠ Warning: could not parse {filename}: {e}")
                else:
                    missing_salary_files.append(filepath)
                    print(f"⚠ Warning: {filename} not found at {filepath}")

            if missing_salary_files:
                print("Note: Some salary files are missing. The analysis will continue but those jobs will be unavailable if selected.")

            return True
            
        except Exception as e:
            print(f"⚠ Data loading failed: {e}")
            return False
    
    def calculate_affordability_index(self, salary, rent, crime_score):
        """
        Calculate comprehensive affordability index
        Index = (Salary / Rent) × Safety Factor
        Safety Factor = 1 / (crime_score + 0.1) to avoid division by zero
        """
        try:
            # Ensure all inputs are numeric
            salary = float(salary)
            rent = float(rent)
            crime_score = float(crime_score)
        
            # Basic affordability ratio (salary to rent ratio)
            if rent > 0:
                affordability_ratio = salary / rent
            else:
                affordability_ratio = 0
        
            # Safety factor (lower crime rate = higher safety factor)
            safety_factor = 1 / crime_score
        
            # Composite index
            composite_index = affordability_ratio * safety_factor * 1000  # Scaling factor for readability
        
            return round(composite_index, 2)
        except (ValueError, TypeError) as e:
            print(f"⚠ Error converting data types: {e}")
            print(f"   Salary: {salary} (type: {type(salary)})")
            print(f"   Rent: {rent} (type: {type(rent)})")
            print(f"   Crime Score: {crime_score} (type: {type(crime_score)})")
            return 0
    
    def get_state_full_name(self, state_abbrev):
        """Convert state abbreviation to full name"""
        return self.state_abbrev.get(state_abbrev.upper(), state_abbrev)
    
    def analyze_cities(self, selected_job, selected_state):
        """Analyze city affordability within specified state"""
        try:
            # Get full state name
            state_full_name = self.get_state_full_name(selected_state)
            
            # Get salary data for selected job
            if selected_job not in self.salary_data:
                print(f"⚠ No salary data found for {selected_job}")
                return None, None
            
            salary_df = self.salary_data[selected_job]
            
            # Get crime data for the state (use abbreviation comparison)
            state_abbr = selected_state.upper()
            state_crime = self.crime_data[self.crime_data['state'].str.upper() == state_abbr]
            if state_crime.empty:
                print(f"⚠ No crime data found for {state_full_name}")
                return None, None
            
            crime_score = state_crime['composite_score'].iloc[0]
            
            # Get rent data for the state
            state_rent_data = self.rent_data[self.rent_data['State'].str.upper() == state_abbr]
            
            # Merge data and calculate index
            results = []
            
            for _, rent_row in state_rent_data.iterrows():
                city_name = rent_row['RegionName']
                avg_rent = rent_row['avg_2024']  # Using average rent of past 12 months
                
                # Find salary data for the city
                city_salary_data = salary_df[salary_df['City'].str.contains(city_name, case=False, na=False)]
                if not city_salary_data.empty:
                    avg_salary = city_salary_data['Salary'].iloc[0]
                    
                    # Calculate composite index
                    index_score = self.calculate_affordability_index(avg_salary, avg_rent, crime_score)
                    
                    results.append({
                        'City': city_name,
                        'Average Salary': avg_salary,
                        'Average Rent': avg_rent,
                        'Affordability Index': index_score
                    })
            
            # Sort by index in descending order and return top 5
            results.sort(key=lambda x: x['Affordability Index'], reverse=True)
            return results[:5], crime_score
            
        except Exception as e:
            print(f"⚠ Error: {e}")
            return None, None
    
    def display_results(self, results, selected_job, selected_state, crime_score):
        """Display analysis results"""
        if not results:
            print("⚠ No matching cities found")
            return
        
        print(f"\n{'-'*80}")
        print(f"{selected_state} State (Crime Score: {crime_score:.2f}) - {selected_job} Position - Top 5 Recommended Cities")
        print(f"{'-'*80}")
        print(f"{'Rank':<4} {'City':<20} {'Avg Salary($)':<12} {'Avg Rent($)':<12} {'Comp. Index':<12}")
        print(f"{'-'*80}")
        
        for i, city_data in enumerate(results, 1):
            print(f"{i:<4} {city_data['City']:<20} {city_data['Average Salary']:<12,.0f} "
                  f"{city_data['Average Rent']:<12,.0f} {city_data['Affordability Index']:<12.2f}")
        
        print(f"{'='*80}")
        print("Note: Composite Index = (Salary / Rent) * (1 / Crime Score) \n Higher composite index indicates better balance between salary, cost of living, and safety")

def if_need_web_scraping(job_mapping):
    def show_menu() -> None:
        print("To get ready to web scrap job data from levels")
        print("Since anti web scrap mechenism in levels.fyi, each time run we up to 1 job updated in dataset\n")
        print("Please select a job title to scrape (0 to skip):")
        for key in sorted(job_mapping.keys(), key=int):
            print(f"{key}. {job_mapping[key]}")
        print("0. No web scraping this time")

    def prompt_choice() -> str:
        valid = set(job_mapping.keys()) | {'0'}
        while True:
            choice = input("Enter a number (0–5): ").strip()
            if choice in valid:
                return choice
            print("Invalid choice. Please enter 0, 1, 2, 3, 4, or 5.")
    

    show_menu()
    choice = prompt_choice()

    if choice == '0':
        print("Okay, skipping web scraping this time.")
        return

    title = job_mapping[choice]
    print(f"You selected: {title}")
    # Pass the NUMBER to your async entrypoint, per your requirement
    asyncio.run(scrape_levels_main(job_mapping[choice]))


def main():
    """Main program"""
    analyzer = CityAffordabilityAnalyzer()
    job_mapping = analyzer.job_mapping

    print("To prepare zillow rent dataset, it should be taken 1 second")
    zillow_to_rent_main()

    print("To prepare fbi crime rate databset, it would take 2 min")
    # fbi_crime_pipeline_main()

    if_need_web_scraping(job_mapping)



    
    # Load data
    if not analyzer.load_data():
        print("⚠ Error: Please check data files.")
        return
    
    while True:
        print("\nPlease select a job position:")
        for key in sorted(job_mapping.keys(), key=int):
            print(f"{key}. {job_mapping[key]}")
        print("0. Exit Program")
        
        job_choice = input("\nEnter job number (0-5): ").strip()
        
        if job_choice == '0':
            print("Thank you for using our system. Goodbye!")
            break
        
        if job_choice not in analyzer.job_mapping:
            print("⚠ Error: Invalid selection. Please try again.")
            continue
        
        selected_job = analyzer.job_mapping[job_choice]
        
        # Input state
        state_input = input("Enter state abbreviation (e.g., CA, NY, TX): ").strip().upper()
        
        if not state_input:
            print("⚠ State name cannot be empty")
            continue
        
        # Perform analysis
        print(f"\nAnalyzing {selected_job} positions in {state_input} state...")
        results, crime_score = analyzer.analyze_cities(selected_job, state_input)
        
        # Display results
        analyzer.display_results(results, selected_job, state_input, crime_score if crime_score is not None else 0)
        
        # Ask to continue
        continue_choice = input("\nContinue analysis? (y/n): ").strip().lower()
        if continue_choice != 'y':
            print("Thank you for using our system. Goodbye!")
            break

if __name__ == "__main__":
    main()
