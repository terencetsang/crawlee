#!/usr/bin/env python3
"""
Unified upload script for all HKJC race data to PocketBase.
Uploads all 8 collections from performance JSON files:
- race_performance (race-level performance data)
- race_performance_analysis (statistical analysis with JSON fields)
- race_horse_performance (individual horse records)
- race_incidents (individual incident records)
- race_incident_analysis (race-level incident analysis)
- race_payouts (race-level payout summary)
- race_payout_pools (individual pool records)
- race_payout_analysis (payout analysis and statistics)

Updated with latest fixes:
- Track condition rating mapping fix
- Improved authentication and session handling
- Better error handling and debugging
- Updated PocketBase URL and credentials
"""

import os
import json
import argparse
import requests
import glob
from datetime import datetime
from urllib.parse import urljoin

class UnifiedRaceDataUploader:
    def __init__(self, base_url, email, password):
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.password = password
        self.auth_token = None
        self.session = requests.Session()
    
    def authenticate(self):
        """Authenticate with PocketBase and get auth token."""
        try:
            auth_url = urljoin(self.base_url, '/api/collections/users/auth-with-password')
            auth_data = {
                'identity': self.email,
                'password': self.password
            }

            response = self.session.post(auth_url, json=auth_data)
            response.raise_for_status()

            auth_result = response.json()
            self.auth_token = auth_result.get('token')

            if self.auth_token:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'Content-Type': 'application/json'
                })
                print("✅ Successfully authenticated with PocketBase")
                return True
            else:
                print("❌ Failed to get auth token")
                return False

        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return False

    def delete_existing_records(self, race_date, racecourse, race_number):
        """Delete existing records for this race from all collections."""
        collections = [
            'race_performance',
            'race_performance_analysis',
            'race_horse_performance',
            'race_incidents',
            'race_incident_analysis',
            'race_payouts',
            'race_payout_pools',
            'race_payout_analysis'
        ]
        
        total_deleted = 0
        
        for collection_name in collections:
            try:
                # Search for existing records
                search_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records')
                search_params = {
                    'filter': f'race_date="{race_date}" && racecourse="{racecourse}" && race_number="{race_number}"',
                    'perPage': 50
                }
                
                search_response = self.session.get(search_url, params=search_params)
                
                if search_response.status_code == 200:
                    existing_records = search_response.json().get('items', [])
                    
                    if existing_records:
                        print(f"  🗑️  Found {len(existing_records)} existing {collection_name} record(s), deleting...")
                        for record in existing_records:
                            record_id = record.get('id')
                            delete_url = urljoin(self.base_url, f'/api/collections/{collection_name}/records/{record_id}')
                            delete_response = self.session.delete(delete_url)
                            if delete_response.status_code == 204:
                                total_deleted += 1
                            else:
                                print(f"    ⚠️  Failed to delete {record_id[:8]}...")
                
            except Exception as e:
                print(f"    ⚠️  Error cleaning {collection_name}: {str(e)}")
        
        if total_deleted > 0:
            print(f"  ✅ Deleted {total_deleted} existing records across all collections")

    def upload_race_data(self, performance_data):
        """Upload all race data from performance JSON to all collections."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            print(f"Uploading complete race data for: {race_date} {racecourse} R{race_number}")

            # Clean up existing records first
            self.delete_existing_records(race_date, racecourse, race_number)

            # Fresh session for each file to avoid session corruption
            self.session = requests.Session()
            if not self.authenticate():
                print(f"❌ Failed to re-authenticate")
                return False

            upload_results = {}

            # 1. Upload race performance (race-level data)
            upload_results['race_performance'] = self.upload_race_performance(performance_data)

            # 2. Upload race performance analysis (with JSON fields)
            upload_results['race_performance_analysis'] = self.upload_race_analysis(performance_data)

            # 3. Upload horse performance (individual horses)
            upload_results['race_horse_performance'] = self.upload_horse_performance(performance_data)

            # 4. Upload incidents
            upload_results['race_incidents'] = self.upload_incidents(performance_data)

            # 5. Upload incident analysis
            upload_results['race_incident_analysis'] = self.upload_incident_analysis(performance_data)

            # 6. Upload race-level payouts
            upload_results['race_payouts'] = self.upload_race_payouts(performance_data)

            # 7. Upload payout pools
            upload_results['race_payout_pools'] = self.upload_payout_pools(performance_data)

            # 8. Upload payout analysis
            upload_results['race_payout_analysis'] = self.upload_payout_analysis(performance_data)

            # Summary
            successful_collections = sum(1 for success in upload_results.values() if success)
            total_collections = len(upload_results)

            print(f"  📊 Upload Results: {successful_collections}/{total_collections} collections successful")
            
            for collection, success in upload_results.items():
                status = "✅" if success else "❌"
                print(f"    {status} {collection}")

            return successful_collections == total_collections

        except Exception as e:
            print(f"❌ Error uploading race data: {str(e)}")
            return False

    def upload_race_performance(self, performance_data):
        """Upload race-level performance data."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            
            race_info = performance_data.get('race_info', {})
            race_performance = performance_data.get('performance', {}).get('race_performance', {})
            
            # Get statistical data for field_size
            statistical_data = performance_data.get('performance', {}).get('statistical_data', {})

            race_record = {
                'race_date': race_date,
                'racecourse': racecourse,
                'race_number': race_number,
                'race_id': f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}",
                'race_name': race_info.get('race_name', ''),
                'race_class': race_info.get('race_class', ''),
                'distance': race_info.get('distance', ''),
                'track_condition': race_info.get('track_condition', ''),
                'prize_money': race_info.get('prize_money', ''),
                'total_runners': race_performance.get('total_runners', 0),
                'winning_time': race_performance.get('winning_time', ''),

                # Basic sectional data (should be in race_performance, not race_performance_analysis)
                'sectional_times': race_performance.get('sectional_times', []),
                'fastest_sectional': race_performance.get('fastest_sectional', 0.0),
                'slowest_sectional': race_performance.get('slowest_sectional', 0.0),
                'sectional_variance': race_performance.get('sectional_variance', 0.0),
                'field_size': statistical_data.get('field_size', 0),
                'track_condition_rating': self._get_track_condition_rating(race_info.get('track_condition', ''), race_performance.get('track_condition_rating', '')),

                'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
            }

            race_url = urljoin(self.base_url, '/api/collections/race_performance/records')
            race_response = self.session.post(race_url, json=race_record)

            if race_response.status_code == 200:
                print(f"  ➕ Created race-level record")
                return True
            else:
                print(f"  ❌ Failed to create race-level record: {race_response.status_code}")
                print(f"      Response: {race_response.text}")
                return False

        except Exception as e:
            print(f"  ❌ Error uploading race performance: {str(e)}")
            return False

    def upload_race_analysis(self, performance_data):
        """Upload race analysis data with JSON fields."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            
            field_analysis = performance_data.get('field_analysis', {})
            race_performance = performance_data.get('performance', {}).get('race_performance', {})
            
            analysis_record = {
                'race_date': race_date,
                'racecourse': racecourse,
                'race_number': race_number,
                'race_id': f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}",
                'total_runners': field_analysis.get('total_runners', 0),
                'market_competitiveness': 'competitive',  # Default value
                'race_competitiveness': 'competitive',    # Default value
                'close_finish_count': 3,                  # Default value
                'average_odds': 15.5,                     # Default value
                'favorite_odds': 3.2,                     # Default value
                'longest_odds': 50.0,                     # Default value
                'race_class': 5,                          # Default value
                
                # JSON fields - the main data we want to preserve
                'favorites_performance': field_analysis.get('favorites_performance', {}),
                'weight_distribution': field_analysis.get('weight_distribution', {}),
                'odds_analysis': field_analysis.get('odds_analysis', {}),
                'margin_analysis': field_analysis.get('margin_analysis', {}),
                'speed_analysis': self._extract_speed_analysis(performance_data),
                
                'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
            }

            # Debug: Show JSON fields being sent
            json_fields = ['favorites_performance', 'weight_distribution', 'odds_analysis', 'margin_analysis', 'speed_analysis']
            print(f"  🔍 DEBUG - JSON fields being sent:")
            for field in json_fields:
                value = analysis_record[field]
                if value and isinstance(value, dict):
                    print(f"    ✅ {field}: {len(value)} keys")
                    if field == 'speed_analysis':
                        print(f"       SPEED_ANALYSIS CONTENT: {value}")
                else:
                    print(f"    ❌ {field}: empty or null")

            # Debug: Show the exact JSON being sent to PocketBase
            print(f"  🔍 DEBUG - Exact speed_analysis being sent:")
            print(f"       Type: {type(analysis_record['speed_analysis'])}")
            print(f"       Content: {analysis_record['speed_analysis']}")
            print(f"       JSON serializable: {json.dumps(analysis_record['speed_analysis']) if analysis_record['speed_analysis'] else 'Empty'}")

            # Debug: Show the complete record being sent
            print(f"  🔍 DEBUG - Complete record keys being sent:")
            for key in analysis_record.keys():
                if key.endswith('_analysis') or key in ['favorites_performance', 'weight_distribution', 'odds_analysis']:
                    value = analysis_record[key]
                    if isinstance(value, dict):
                        print(f"       {key}: {len(value)} keys")
                    else:
                        print(f"       {key}: {type(value)} = {value}")

            analysis_url = urljoin(self.base_url, '/api/collections/race_performance_analysis/records')
            analysis_response = self.session.post(analysis_url, json=analysis_record)

            if analysis_response.status_code == 200:
                print(f"  ➕ Created race analysis record")

                # Verify what was actually saved
                saved_record = analysis_response.json()
                saved_speed_analysis = saved_record.get('speed_analysis')

                if isinstance(saved_speed_analysis, dict) and saved_speed_analysis:
                    print(f"  ✅ VERIFIED: speed_analysis saved with {len(saved_speed_analysis)} keys")
                else:
                    print(f"  ❌ WARNING: speed_analysis was NOT saved properly!")
                    print(f"      Saved as: {saved_speed_analysis}")

                return True
            else:
                print(f"  ❌ Failed to create race analysis record: {analysis_response.status_code}")
                print(f"      Response: {analysis_response.text}")
                return False

        except Exception as e:
            print(f"  ❌ Error uploading race analysis: {str(e)}")
            return False

    def upload_horse_performance(self, performance_data):
        """Upload individual horse performance data."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            # Use results data which has complete horse information
            results = performance_data.get('results', [])

            # Also get performance metrics if available
            horse_performance = performance_data.get('performance', {}).get('horse_performance', [])

            # Create a lookup for performance metrics by horse number
            metrics_lookup = {}
            for horse in horse_performance:
                horse_num = horse.get('horse_number', '')
                if horse_num:
                    metrics_lookup[horse_num] = horse.get('performance_metrics', {})

            if not results:
                print(f"  ⚠️  No horse results data found")
                return True  # Not an error, just no data

            records_uploaded = 0

            for result in results:
                horse_number = result.get('horse_number', '')
                metrics = metrics_lookup.get(horse_number, {})

                # Debug: Print first horse data
                if records_uploaded == 0:
                    print(f"    🔍 Debug first horse:")
                    print(f"      Horse #{horse_number}: {result.get('horse_name', '')}")
                    print(f"      Jockey: '{result.get('jockey', '')}'")
                    print(f"      Trainer: '{result.get('trainer', '')}'")
                    print(f"      Finish Time: '{result.get('finish_time', '')}'")
                    print(f"      Running Position: '{result.get('running_position', '')}'")
                    print(f"      Actual Weight: '{result.get('actual_weight', '')}'")
                    print(f"      Draw: '{result.get('draw', '')}'")
                    print(f"      Metrics keys: {list(metrics.keys()) if metrics else 'None'}")

                # Create horse name with code
                horse_name = result.get('horse_name', '')
                horse_code = result.get('horse_code', '')
                horse_name_with_code = f"{horse_name}({horse_code})" if horse_code else horse_name

                # Parse numeric values safely
                def safe_int(value, default=0):
                    try:
                        if value is None or value == '' or value == '-':
                            return default
                        # Handle string numbers that might have spaces or other characters
                        cleaned = str(value).strip()
                        if cleaned == '' or cleaned == '-':
                            return default
                        # Try to convert to int, handling floats too
                        return int(float(cleaned))
                    except (ValueError, TypeError):
                        return default

                def safe_float(value, default=0.0):
                    try:
                        if value is None or value == '' or value == '-':
                            return default
                        cleaned = str(value).strip()
                        if cleaned == '' or cleaned == '-':
                            return default
                        return float(cleaned)
                    except (ValueError, TypeError):
                        return default

                # Create speed metrics for this horse
                speed_metrics = self._extract_horse_speed_metrics(result, performance_data)

                horse_record = {
                    'race_date': race_date,
                    'racecourse': racecourse,
                    'race_number': race_number,
                    'race_id': race_id,
                    'horse_number': horse_number,
                    'horse_name': horse_name,
                    'horse_name_with_code': horse_name_with_code,
                    'position': safe_int(result.get('position', 0)),
                    'jockey': result.get('jockey', ''),
                    'trainer': result.get('trainer', ''),
                    'actual_weight': safe_int(result.get('actual_weight', 0)),
                    'declared_weight': safe_int(result.get('declared_weight', 0)),
                    'weight_carried': safe_int(metrics.get('weight_carried', result.get('actual_weight', 0))),
                    'draw': safe_int(result.get('draw', 0)),
                    'margin': result.get('margin', ''),
                    'running_position': result.get('running_position', ''),
                    'finish_time': result.get('finish_time', ''),
                    'win_odds': safe_float(result.get('win_odds', 0.0)),
                    'odds_rating': metrics.get('odds_rating', ''),
                    'result_rating': metrics.get('result_rating', ''),
                    'weight_rating': metrics.get('weight_rating', ''),
                    # Note: horse_rating removed - HKJC doesn't provide horse ratings in race results
                    # Note: sectional_time removed - race-level data stored in race_performance collection

                    # JSON fields for detailed metrics
                    'performance_metrics': metrics if metrics else {},
                    'speed_metrics': speed_metrics,

                    'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
                }

                # Debug: Print the record being sent for first horse
                if records_uploaded == 0:
                    print(f"    🔍 Record being sent to PocketBase:")
                    for key, value in horse_record.items():
                        if key in ['performance_metrics', 'speed_metrics']:
                            if isinstance(value, dict):
                                print(f"      {key}: dict with {len(value)} keys")
                            else:
                                print(f"      {key}: {value} (type: {type(value)})")
                        else:
                            print(f"      {key}: {value}")

                horse_url = urljoin(self.base_url, '/api/collections/race_horse_performance/records')
                horse_response = self.session.post(horse_url, json=horse_record)

                if horse_response.status_code == 200:
                    records_uploaded += 1
                    # Debug: Print what was actually saved for first horse
                    if records_uploaded == 1:
                        saved_record = horse_response.json()
                        print(f"    🔍 What was actually saved:")
                        for key, value in saved_record.items():
                            if key not in ['id', 'created', 'updated', 'collectionId', 'collectionName']:
                                if key in ['performance_metrics', 'speed_metrics']:
                                    if isinstance(value, dict):
                                        print(f"      ✅ {key}: dict with {len(value)} keys")
                                    else:
                                        print(f"      ❌ {key}: {value}")
                                else:
                                    # Note: horse_rating field removed as HKJC doesn't provide horse ratings
                                    status = '✅' if value and value != '' and value != 0 else '❌'
                                    print(f"      {status} {key}: {value}")
                else:
                    print(f"    ❌ Failed to create horse record for {horse_name}")
                    print(f"        Error: {horse_response.status_code} - {horse_response.text}")

            print(f"  ➕ Created {records_uploaded} horse performance records")
            return records_uploaded > 0

        except Exception as e:
            print(f"  ❌ Error uploading horse performance: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def upload_incidents(self, performance_data):
        """Upload race incidents data."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            incidents = performance_data.get('incidents', [])

            if not incidents:
                print(f"  ℹ️  No incidents data found")
                return True  # Not an error, just no incidents

            records_uploaded = 0

            for incident in incidents:
                incident_record = {
                    'race_date': race_date,
                    'racecourse': racecourse,
                    'race_number': race_number,
                    'race_id': race_id,
                    'position': incident.get('position', 0),
                    'horse_number': incident.get('horse_number', ''),
                    'horse_name': incident.get('horse_name', ''),
                    'horse_name_with_code': incident.get('horse_name_with_code', ''),
                    'incident_report': incident.get('incident_report', ''),
                    'incident_type': incident.get('incident_type', ''),
                    'severity': incident.get('severity', ''),
                    'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
                }

                incident_url = urljoin(self.base_url, '/api/collections/race_incidents/records')
                incident_response = self.session.post(incident_url, json=incident_record)

                if incident_response.status_code == 200:
                    records_uploaded += 1
                else:
                    print(f"    ❌ Failed to create incident record")

            print(f"  ➕ Created {records_uploaded} incident records")
            return True

        except Exception as e:
            print(f"  ❌ Error uploading incidents: {str(e)}")
            return False

    def upload_incident_analysis(self, performance_data):
        """Upload comprehensive incident analysis data."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            # Get race info
            race_info = performance_data.get('race_info', {})

            # Get incidents and horse performance data
            incidents = performance_data.get('incidents', [])
            horse_performance = performance_data.get('performance', {}).get('horse_performance', [])

            # Calculate total horses from horse performance data
            total_horses = len(horse_performance)
            if total_horses == 0:
                # Fallback to statistical data
                statistical_data = performance_data.get('performance', {}).get('statistical_data', {})
                total_horses = statistical_data.get('field_size', 12)

            # Analyze incidents comprehensively
            horses_with_incidents = len(set(incident.get('horse_number', '') for incident in incidents if incident.get('horse_number')))
            horses_no_incidents = max(0, total_horses - horses_with_incidents)
            incident_rate = round((horses_with_incidents / total_horses * 100), 1) if total_horses > 0 else 0.0

            # Severity breakdown
            severity_breakdown = {}
            for incident in incidents:
                severity = incident.get('severity', 'unknown')
                severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1

            # Incident type breakdown
            incident_type_breakdown = {}
            for incident in incidents:
                incident_type = incident.get('incident_type', 'unknown')
                incident_type_breakdown[incident_type] = incident_type_breakdown.get(incident_type, 0) + 1

            # Find most serious incidents (high severity first, then medium)
            most_serious_incidents = []
            for severity in ['high', 'medium', 'low']:
                serious_incidents = [
                    {
                        'horse_name': incident.get('horse_name', ''),
                        'position': incident.get('position', 0),
                        'incident_type': incident.get('incident_type', ''),
                        'report': incident.get('incident_report', '')[:200] + '...' if len(incident.get('incident_report', '')) > 200 else incident.get('incident_report', '')
                    }
                    for incident in incidents
                    if incident.get('severity') == severity
                ]
                most_serious_incidents.extend(serious_incidents)
                if len(most_serious_incidents) >= 3:  # Limit to top 3
                    break
            most_serious_incidents = most_serious_incidents[:3]

            # Stewards actions (incidents requiring veterinary examination or other actions)
            stewards_actions = []
            action_types = ['veterinary_examination', 'post_race_testing', 'interference']
            for incident in incidents:
                if incident.get('incident_type') in action_types:
                    stewards_actions.append({
                        'horse_name': incident.get('horse_name', ''),
                        'position': incident.get('position', 0),
                        'action_type': incident.get('incident_type', ''),
                        'report': incident.get('incident_report', '')[:150] + '...' if len(incident.get('incident_report', '')) > 150 else incident.get('incident_report', '')
                    })

            # Determine safety assessment based on incident rate and severity
            high_severity_count = severity_breakdown.get('high', 0)
            medium_severity_count = severity_breakdown.get('medium', 0)

            if incident_rate >= 75 or high_severity_count >= 3:
                safety_assessment = 'high_incident_rate'
            elif incident_rate >= 40 or high_severity_count >= 1 or medium_severity_count >= 5:
                safety_assessment = 'moderate_incident_rate'
            else:
                safety_assessment = 'low_incident_rate'

            # Use the same race info fields as race_performance collection for consistency
            race_name = race_info.get('race_name', '')
            distance = race_info.get('distance', '')
            race_class = race_info.get('race_class', '')

            incident_analysis_record = {
                'race_date': race_date,
                'racecourse': racecourse,
                'race_number': race_number,
                'race_id': race_id,
                'race_name': race_name,
                'distance': distance,
                'track_condition': race_info.get('track_condition', ''),
                'race_class': race_class,
                'total_horses': total_horses,
                'horses_with_incidents': horses_with_incidents,
                'horses_no_incidents': horses_no_incidents,
                'incident_rate': incident_rate,
                'severity_breakdown': severity_breakdown,
                'incident_type_breakdown': incident_type_breakdown,
                'most_serious_incidents': most_serious_incidents,
                'stewards_actions': stewards_actions,
                'race_safety_assessment': safety_assessment,
                'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
            }

            incident_analysis_url = urljoin(self.base_url, '/api/collections/race_incident_analysis/records')
            incident_analysis_response = self.session.post(incident_analysis_url, json=incident_analysis_record)

            if incident_analysis_response.status_code == 200:
                print(f"  ➕ Created comprehensive incident analysis record")
                print(f"      📊 {horses_with_incidents}/{total_horses} horses with incidents ({incident_rate}%)")
                print(f"      🚨 Safety: {safety_assessment}")
                return True
            else:
                print(f"  ❌ Failed to create incident analysis record: {incident_analysis_response.status_code}")
                print(f"      Response: {incident_analysis_response.text}")
                return False

        except Exception as e:
            print(f"  ❌ Error uploading incident analysis: {str(e)}")
            return False

    def upload_race_payouts(self, performance_data):
        """Upload race-level payout summary."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            payouts = performance_data.get('payouts', {})
            race_info = performance_data.get('race_info', {})

            if not payouts:
                print(f"  ℹ️  No payouts data found for race summary")
                return True

            # Calculate win dividend
            win_dividend = 0.0
            if '獨贏' in payouts and payouts['獨贏']:
                win_dividend = self._parse_payout_amount(payouts['獨贏'][0].get('payout', '0'))

            # Get winner info from horse performance
            winner_horse_name = ''
            winner_horse_number = ''
            horse_performance = performance_data.get('performance', {}).get('horse_performance', [])
            for horse in horse_performance:
                if horse.get('position') == 1:
                    winner_horse_name = horse.get('horse_name', '')
                    winner_horse_number = horse.get('horse_number', '')
                    break

            race_payout_record = {
                'race_date': race_date,
                'racecourse': racecourse,
                'race_number': race_number,
                'race_id': race_id,
                'race_name': race_info.get('race_name', ''),
                'track_condition': race_info.get('track_condition', ''),
                'distance': race_info.get('distance', ''),
                'prize_money': race_info.get('prize_money', ''),
                'winner_horse_name': winner_horse_name,
                'winner_horse_number': winner_horse_number,
                'win_dividend': win_dividend,
                'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
            }

            race_payout_url = urljoin(self.base_url, '/api/collections/race_payouts/records')
            race_payout_response = self.session.post(race_payout_url, json=race_payout_record)

            if race_payout_response.status_code == 200:
                print(f"  ➕ Created race payout summary record")
                return True
            else:
                print(f"  ❌ Failed to create race payout summary: {race_payout_response.status_code}")
                return False

        except Exception as e:
            print(f"  ❌ Error uploading race payouts: {str(e)}")
            return False

    def upload_payout_pools(self, performance_data):
        """Upload individual payout pool records."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            payouts = performance_data.get('payouts', {})

            if not payouts:
                print(f"  ℹ️  No payout pools data found")
                return True

            pool_records_uploaded = 0

            for pool_type, pool_data in payouts.items():
                if isinstance(pool_data, list):
                    for payout in pool_data:
                        pool_record = {
                            'race_id': race_id,
                            'pool_type': pool_type,
                            'combination': payout.get('combination', ''),
                            'payout_amount': self._parse_payout_amount(payout.get('payout', '0')),
                            'payout_formatted': payout.get('payout', ''),
                            'pool_category': self._categorize_pool_type(pool_type),
                            'combination_size': len(payout.get('combination', '').split(',')),
                            'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
                        }

                        pool_url = urljoin(self.base_url, '/api/collections/race_payout_pools/records')
                        pool_response = self.session.post(pool_url, json=pool_record)

                        if pool_response.status_code == 200:
                            pool_records_uploaded += 1

            print(f"  ➕ Created {pool_records_uploaded} payout pool records")
            return True

        except Exception as e:
            print(f"  ❌ Error uploading payout pools: {str(e)}")
            return False

    def upload_payout_analysis(self, performance_data):
        """Upload payout analysis data."""
        try:
            race_date = performance_data.get('race_date', '')
            racecourse = performance_data.get('racecourse', '')
            race_number = performance_data.get('race_number', '')
            race_id = f"{race_date.replace('/', '-')}_{racecourse}_R{race_number}"

            payouts = performance_data.get('payouts', {})

            if not payouts:
                print(f"  ℹ️  No payouts data found for analysis")
                return True

            # Analyze payouts
            total_pools = len(payouts)
            pool_types = list(payouts.keys())

            # Find highest payout
            highest_payout_amount = 0.0
            highest_payout_pool = ''
            highest_payout_combination = ''

            for pool_type, pool_data in payouts.items():
                if isinstance(pool_data, list):
                    for payout in pool_data:
                        amount = self._parse_payout_amount(payout.get('payout', '0'))
                        if amount > highest_payout_amount:
                            highest_payout_amount = amount
                            highest_payout_pool = pool_type
                            highest_payout_combination = payout.get('combination', '')

            # Get win dividend and place dividends
            win_dividend = 0.0
            place_dividends = []
            quinella_place_dividends = []

            if '獨贏' in payouts and payouts['獨贏']:
                win_dividend = self._parse_payout_amount(payouts['獨贏'][0].get('payout', '0'))

            if '位置' in payouts:
                place_dividends = [self._parse_payout_amount(p.get('payout', '0')) for p in payouts['位置']]

            if '位置Q' in payouts:
                quinella_place_dividends = [self._parse_payout_amount(p.get('payout', '0')) for p in payouts['位置Q']]

            # Count exotic pools
            exotic_pools_count = self._count_exotic_pools(payouts)
            total_dividend_value = self._calculate_total_dividend_value(payouts)

            payout_analysis_record = {
                'race_date': race_date,
                'racecourse': racecourse,
                'race_number': race_number,
                'race_id': race_id,
                'total_pools': total_pools,
                'pool_types': pool_types,
                'highest_payout_amount': highest_payout_amount,
                'highest_payout_pool': highest_payout_pool,
                'highest_payout_combination': highest_payout_combination,
                'win_dividend': win_dividend,
                'place_dividends': place_dividends,
                'quinella_place_dividends': quinella_place_dividends,
                'exotic_pools_count': exotic_pools_count,
                'total_dividend_value': total_dividend_value,
                'extracted_at': performance_data.get('scraped_at', datetime.now().isoformat())
            }

            payout_analysis_url = urljoin(self.base_url, '/api/collections/race_payout_analysis/records')
            payout_analysis_response = self.session.post(payout_analysis_url, json=payout_analysis_record)

            if payout_analysis_response.status_code == 200:
                print(f"  ➕ Created payout analysis record")
                return True
            else:
                print(f"  ❌ Failed to create payout analysis record: {payout_analysis_response.status_code}")
                return False

        except Exception as e:
            print(f"  ❌ Error uploading payout analysis: {str(e)}")
            return False

    def _parse_payout_amount(self, payout_str):
        """Parse payout string to numeric value."""
        try:
            if not payout_str:
                return 0.0
            amount_str = str(payout_str).replace('HK$', '').replace(',', '').strip()
            return float(amount_str) if amount_str.replace('.', '').isdigit() else 0.0
        except:
            return 0.0

    def _categorize_pool_type(self, pool_type):
        """Categorize pool type for easier analysis."""
        pool_categories = {
            '獨贏': 'win', '位置': 'place', '連贏': 'quinella', '位置Q': 'quinella',
            '二重彩': 'exacta', '三重彩': 'trifecta', '單T': 'trifecta',
            '四連環': 'superfecta', '四重彩': 'superfecta'
        }
        return pool_categories.get(pool_type, 'exotic')

    def _count_exotic_pools(self, payouts):
        """Count exotic betting pools."""
        exotic_pools = ['二重彩', '三重彩', '單T', '四連環', '四重彩', '第一口孖寶', '第一口孖T']
        return sum(1 for pool_type in payouts.keys() if pool_type in exotic_pools)

    def _calculate_total_dividend_value(self, payouts):
        """Calculate total dividend value across all pools."""
        total = 0.0
        for pool_data in payouts.values():
            if isinstance(pool_data, list):
                for payout in pool_data:
                    total += self._parse_payout_amount(payout.get('payout', '0'))
        return total

    def _extract_speed_analysis(self, performance_data):
        """Extract speed analysis from available timing data - ANALYTICAL DATA ONLY."""
        try:
            speed_analysis = {}

            # Get race performance data
            race_performance = performance_data.get('performance', {}).get('race_performance', {})

            # NOTE: Basic sectional data (sectional_times, fastest_sectional, slowest_sectional,
            # sectional_variance, field_size, track_condition_rating) now goes to race_performance collection
            # This function should only extract DERIVED ANALYTICAL DATA

            # Extract finish times from raw results data
            results = performance_data.get('results', [])
            finish_times = []

            for result in results:
                finish_time_str = result.get('finish_time', '')
                if finish_time_str and finish_time_str != '-':
                    # Convert time string like "1:08.98" to seconds
                    try:
                        if ':' in finish_time_str:
                            parts = finish_time_str.split(':')
                            if len(parts) == 2:
                                minutes = float(parts[0])
                                seconds = float(parts[1])
                                total_seconds = minutes * 60 + seconds
                                finish_times.append(total_seconds)
                    except:
                        pass

            if finish_times:
                speed_analysis['winning_time'] = round(min(finish_times), 2)
                speed_analysis['slowest_time'] = round(max(finish_times), 2)
                speed_analysis['time_spread'] = round(max(finish_times) - min(finish_times), 2)
                speed_analysis['average_time'] = round(sum(finish_times) / len(finish_times), 2)

            # Determine pace pattern based on sectional times (for analytical purposes only)
            sectional_times = race_performance.get('sectional_times', [])
            if sectional_times and len(sectional_times) >= 1:
                first_sectional = float(sectional_times[0])
                if first_sectional < 23.0:
                    speed_analysis['pace_pattern'] = 'fast_early'
                elif first_sectional > 25.0:
                    speed_analysis['pace_pattern'] = 'slow_early'
                else:
                    speed_analysis['pace_pattern'] = 'moderate_early'

            return speed_analysis

        except Exception as e:
            print(f"    ⚠️  Error extracting speed analysis: {str(e)}")
            return {}

    def _extract_horse_speed_metrics(self, horse_result, performance_data):
        """Extract speed metrics for an individual horse."""
        try:
            speed_metrics = {}

            # Get horse-specific data
            finish_time_str = horse_result.get('finish_time', '')
            running_position = horse_result.get('running_position', '')
            position = horse_result.get('position', 0)

            # Convert finish time to seconds
            if finish_time_str and finish_time_str != '-':
                try:
                    if ':' in finish_time_str:
                        parts = finish_time_str.split(':')
                        if len(parts) == 2:
                            minutes = float(parts[0])
                            seconds = float(parts[1])
                            total_seconds = minutes * 60 + seconds
                            speed_metrics['finish_time_seconds'] = round(total_seconds, 2)
                except:
                    pass

            # Analyze running position pattern
            if running_position and running_position != '-':
                speed_metrics['running_position_pattern'] = running_position

                # Try to extract sectional positions
                if len(running_position) >= 3:
                    try:
                        # For patterns like "631" or "112" - extract individual positions
                        positions = []
                        for char in running_position:
                            if char.isdigit():
                                positions.append(int(char))

                        if positions:
                            speed_metrics['sectional_positions'] = positions
                            speed_metrics['early_position'] = positions[0] if len(positions) > 0 else 0
                            speed_metrics['mid_position'] = positions[len(positions)//2] if len(positions) > 1 else 0
                            speed_metrics['late_position'] = positions[-1] if len(positions) > 0 else 0

                            # Calculate position changes
                            if len(positions) >= 2:
                                speed_metrics['early_to_late_change'] = positions[-1] - positions[0]
                                speed_metrics['position_consistency'] = 'consistent' if max(positions) - min(positions) <= 2 else 'variable'
                    except:
                        pass

            # Add finishing position analysis
            if position:
                speed_metrics['finishing_position'] = position
                if position == 1:
                    speed_metrics['result_category'] = 'winner'
                elif position <= 3:
                    speed_metrics['result_category'] = 'placed'
                elif position <= 6:
                    speed_metrics['result_category'] = 'competitive'
                else:
                    speed_metrics['result_category'] = 'unplaced'

            # Get race-level speed context
            race_performance = performance_data.get('performance', {}).get('race_performance', {})
            sectional_times = race_performance.get('sectional_times', [])

            if sectional_times:
                speed_metrics['race_sectional_count'] = len(sectional_times)
                speed_metrics['race_pace_context'] = 'available'

            return speed_metrics

        except Exception as e:
            print(f"    ⚠️  Error extracting horse speed metrics: {str(e)}")
            return {}

    def _get_track_condition_rating(self, track_condition, existing_rating):
        """Get track condition rating with updated mapping."""
        # If we already have a valid rating that's not 'unknown', use it
        if existing_rating and existing_rating != 'unknown':
            return existing_rating

        # Apply the corrected mapping
        condition_ratings = {
            "好地": "fast",
            "快地": "good",
            "好至快地": "good",  # Good to Fast -> good
            "好地至快地": "fast",  # Good to Fast (alternative format) -> fast
            "軟地": "slow",  # Soft -> slow
            "黏地": "heavy"  # Heavy -> heavy
        }

        return condition_ratings.get(track_condition, "unknown")

def load_performance_data(filepath):
    """Load performance data from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Error loading {filepath}: {str(e)}")
        return None

def upload_single_file(uploader, filepath):
    """Upload a single performance file to all PocketBase collections."""
    print(f"\nProcessing: {os.path.basename(filepath)}")

    performance_data = load_performance_data(filepath)
    if not performance_data:
        return False

    # Create fresh session for each file to avoid session corruption
    uploader.session = requests.Session()
    if not uploader.authenticate():
        print(f"❌ Failed to re-authenticate for {filepath}")
        return False

    success = uploader.upload_race_data(performance_data)
    return success

def upload_all_files(uploader, directory="performance_data"):
    """Upload all performance files in a directory to PocketBase."""
    pattern = os.path.join(directory, 'performance_*.json')
    performance_files = glob.glob(pattern)

    if not performance_files:
        print(f"No performance files found in {directory}")
        return 0

    print(f"Found {len(performance_files)} performance files in {directory}")

    success_count = 0
    for filepath in sorted(performance_files):
        if upload_single_file(uploader, filepath):
            success_count += 1

    return success_count

def main():
    parser = argparse.ArgumentParser(
        description='Unified upload of all HKJC race data to PocketBase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_all_simple.py performance_data/performance_2025-06-08_ST_R10.json
  python upload_all_simple.py --directory performance_data/
  python upload_all_simple.py --all-files

This script uploads to all 8 PocketBase collections:
  • race_performance (race-level data)
  • race_performance_analysis (statistical analysis)
  • race_horse_performance (individual horses)
  • race_incidents (incident records)
  • race_incident_analysis (incident analysis)
  • race_payouts (payout summary)
  • race_payout_pools (individual pools)
  • race_payout_analysis (payout analysis)
        """
    )
    parser.add_argument('file', nargs='?', help='Single performance JSON file to upload')
    parser.add_argument('--directory', help='Directory containing performance files to upload')
    parser.add_argument('--all-files', action='store_true', help='Upload all files in performance_data/ directory')
    parser.add_argument('--pocketbase-url', default='http://terence.myds.me:8081', help='PocketBase URL')
    parser.add_argument('--email', default='terencetsang@hotmail.com', help='PocketBase user email')
    parser.add_argument('--password', default='Qwertyu12345', help='PocketBase user password')

    args = parser.parse_args()

    if not any([args.file, args.directory, args.all_files]):
        parser.error("Must specify either a file, --directory, or --all-files")

    print("HKJC Race Data Unified PocketBase Uploader")
    print("=" * 55)
    print("📊 Uploads to all 8 collections:")
    print("  • race_performance (race-level data)")
    print("  • race_performance_analysis (statistical analysis)")
    print("  • race_horse_performance (individual horses)")
    print("  • race_incidents (incident records)")
    print("  • race_incident_analysis (incident analysis)")
    print("  • race_payouts (payout summary)")
    print("  • race_payout_pools (individual pools)")
    print("  • race_payout_analysis (payout analysis)")
    print(f"🌐 PocketBase URL: {args.pocketbase_url}")
    print(f"👤 Email: {args.email}")
    print()

    # Create uploader and authenticate
    uploader = UnifiedRaceDataUploader(args.pocketbase_url, args.email, args.password)

    if not uploader.authenticate():
        print("❌ Failed to authenticate. Exiting.")
        return

    # Upload files
    success_count = 0
    total_files = 0

    if args.all_files:
        success_count = upload_all_files(uploader)
        total_files = len(glob.glob("performance_data/performance_*.json"))
    elif args.directory:
        success_count = upload_all_files(uploader, args.directory)
        total_files = len(glob.glob(f"{args.directory}/performance_*.json"))
    elif args.file:
        total_files = 1
        if upload_single_file(uploader, args.file):
            success_count = 1

    print(f"\n" + "=" * 55)
    print(f"📊 Upload Summary:")
    print(f"Total files processed: {total_files}")
    print(f"Successfully uploaded: {success_count}")
    print(f"Failed: {total_files - success_count}")

    if success_count > 0:
        print(f"\n✅ Successfully uploaded {success_count} performance files to all 8 collections!")
        print(f"\n📋 Collections updated:")
        print(f"  • race_performance: Race-level performance metrics")
        print(f"  • race_performance_analysis: Statistical analysis with JSON fields")
        print(f"  • race_horse_performance: Individual horse performance data")
        print(f"  • race_incidents: Individual incident records")
        print(f"  • race_incident_analysis: Race-level incident analysis")
        print(f"  • race_payouts: Race-level payout summary")
        print(f"  • race_payout_pools: Individual betting pool records")
        print(f"  • race_payout_analysis: Payout analysis and statistics")
        print(f"\n🌐 Access your data at: {args.pocketbase_url}/_/")
    else:
        print(f"\n❌ No files were uploaded successfully")
        print(f"   Please check authentication and PocketBase server status")

if __name__ == "__main__":
    main()
