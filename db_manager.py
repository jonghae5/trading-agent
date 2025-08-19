import sqlite3
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
import hashlib
import secrets
import pandas as pd
import pytz

# KST 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """현재 KST 시간을 naive datetime으로 반환"""
    return datetime.datetime.now(KST).replace(tzinfo=None)

def get_kst_naive_now():
    """현재 KST 시간을 naive datetime으로 반환 (호환성)"""
    return get_kst_now()

class DatabaseManager:
    """통합 데이터베이스 매니저 - 사용자 관리, 분석 리포트 히스토리 통합"""
    
    def __init__(self, db_path: str = "trading_agents.db"):
        self.db_path = Path(db_path)
        self.init_database()
        self.cleanup_invalid_sessions()
    
    def init_database(self):
        """데이터베이스 초기화 및 모든 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            # 사용자 관리 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME NULL,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until DATETIME NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 사용자 세션 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (username) REFERENCES users (username)
                )
            ''')
            
            # 분석 세션 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    analysis_date DATETIME NOT NULL,
                    status TEXT NOT NULL,  -- 'running', 'completed', 'failed'
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME NULL,
                    final_decision TEXT NULL,  -- 'BUY', 'HOLD', 'SELL'
                    confidence_score REAL NULL,
                    execution_time_seconds REAL NULL,  -- 분석 실행 시간 (초)
                    config_snapshot TEXT NULL,  -- JSON 형태로 분석 설정 저장
                    FOREIGN KEY (username) REFERENCES users (username)
                )
            ''')
            
            # 리포트 섹션 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS report_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    section_type TEXT NOT NULL,  -- 'market_report', 'sentiment_report', etc.
                    agent_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES analysis_sessions (session_id)
                )
            ''')
            
            # 에이전트 실행 로그 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    status TEXT NOT NULL,  -- 'pending', 'running', 'completed', 'failed'
                    started_at DATETIME NULL,
                    completed_at DATETIME NULL,
                    execution_time_seconds REAL NULL,
                    error_message TEXT NULL,
                    FOREIGN KEY (session_id) REFERENCES analysis_sessions (session_id)
                )
            ''')
            
            # 사용자 설정 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES users (username),
                    UNIQUE(username, preference_key)
                )
            ''')
            
            # 인덱스 생성
            conn.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_username ON user_sessions (username)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions (expires_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_analysis_user_date ON analysis_sessions (username, analysis_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_analysis_ticker ON analysis_sessions (ticker)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_report_sections_session ON report_sections (session_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_agent_executions_session ON agent_executions (session_id)')
            
            # 데이터베이스 마이그레이션
            self._migrate_database()
            
            # 기본 사용자 생성 (개발용)
            self._create_default_users()
    
    def _migrate_database(self):
        """데이터베이스 스키마 마이그레이션"""
        with sqlite3.connect(self.db_path) as conn:
            # execution_time_seconds 컬럼이 없으면 추가
            try:
                cursor = conn.execute("PRAGMA table_info(analysis_sessions)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'execution_time_seconds' not in columns:
                    conn.execute('ALTER TABLE analysis_sessions ADD COLUMN execution_time_seconds REAL NULL')
                    print("Added execution_time_seconds column to analysis_sessions table")
            except Exception as e:
                print(f"Migration warning: {e}")
    
    def _create_default_users(self):
        """기본 사용자 생성"""
        default_users = [
            {"username": "jh", "password": "jonghae5"},
            {"username": "admin", "password": "admin123"},
            {"username": "analyst", "password": "analyst123"}
        ]
        
        for user_data in default_users:
            try:
                self.create_user(user_data["username"], user_data["password"])
            except ValueError:
                # 이미 존재하는 사용자는 무시
                pass
    
    # =============================================================================
    # 사용자 관리 메서드
    # =============================================================================
    
    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """비밀번호 해시 생성"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex(), salt
    
    def create_user(self, username: str, password: str) -> bool:
        """사용자 생성"""
        password_hash, salt = self._hash_password(password)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO users (username, password_hash, salt)
                    VALUES (?, ?, ?)
                ''', (username, password_hash, salt))
                return True
        except sqlite3.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
    
    def verify_user(self, username: str, password: str) -> bool:
        """사용자 인증"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT password_hash, salt, login_attempts, locked_until
                FROM users 
                WHERE username = ? AND is_active = 1
            ''', (username,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            stored_hash, salt, login_attempts, locked_until = result
            
            # 계정 잠금 확인
            if locked_until:
                locked_until_dt = datetime.datetime.fromisoformat(locked_until)
                if datetime.datetime.now() < locked_until_dt:
                    return False
                else:
                    # 잠금 해제
                    conn.execute('''
                        UPDATE users SET locked_until = NULL, login_attempts = 0
                        WHERE username = ?
                    ''', (username,))
            
            # 비밀번호 검증
            password_hash, _ = self._hash_password(password, salt)
            
            if password_hash == stored_hash:
                # 로그인 성공
                conn.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, login_attempts = 0
                    WHERE username = ?
                ''', (username,))
                return True
            else:
                # 로그인 실패
                new_attempts = login_attempts + 1
                locked_until = None
                
                if new_attempts >= 5:  # 5회 실패시 1시간 잠금
                    locked_until = datetime.datetime.now() + datetime.timedelta(hours=1)
                    conn.execute('''
                        UPDATE users 
                        SET login_attempts = ?, locked_until = ?
                        WHERE username = ?
                    ''', (new_attempts, locked_until.isoformat(), username))
                else:
                    conn.execute('''
                        UPDATE users 
                        SET login_attempts = ?
                        WHERE username = ?
                    ''', (new_attempts, username))
                
                return False
    
    def create_session(self, username: str, duration_hours: int = 1) -> str:
        """사용자 세션 생성 (KST naive datetime으로 통일)"""
        session_id = secrets.token_urlsafe(32)
        # KST 시간을 naive datetime으로 변환해서 저장
        current_kst = get_kst_now()
        expires_at = current_kst + datetime.timedelta(hours=duration_hours)
        
        print(f"[DB] Creating user session - User: {username}, Duration: {duration_hours}h, Session ID: {session_id[:8]}...")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_sessions (session_id, username, expires_at, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, username, expires_at.isoformat(), current_kst.isoformat(), current_kst.isoformat()))
        
        print(f"[DB] ✅ User session created: {username} -> {session_id[:8]}")
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """세션 유효성 검사 및 사용자명 반환 (KST 기준)"""
        print(f"[DB] Validating session: {session_id[:8]}...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT username, expires_at 
                FROM user_sessions 
                WHERE session_id = ? AND is_active = 1
            ''', (session_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"[DB] ❌ Session not found or inactive: {session_id[:8]}")
                return None
            
            username, expires_at = result
            
            expires_at_dt = datetime.datetime.fromisoformat(expires_at)
            
            # KST 기준으로 현재 시간 가져오기
            current_kst = get_kst_now()
            
            # expires_at도 강제로 naive로 변환
            if expires_at_dt.tzinfo is not None:
                expires_at_dt = expires_at_dt.replace(tzinfo=None)
            
            if current_kst > expires_at_dt:
                # 세션 만료
                print(f"[DB] ❌ Session expired: {session_id[:8]} (user: {username})")
                self.invalidate_session(session_id)
                return None
            
            # 마지막 활동 시간 업데이트 (KST)
            conn.execute('''
                UPDATE user_sessions 
                SET last_activity = ?
                WHERE session_id = ?
            ''', (get_kst_now().isoformat(), session_id))
            
            print(f"[DB] ✅ Session valid: {session_id[:8]} -> {username}")
            return username
    
    def invalidate_session(self, session_id: str):
        """세션 무효화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE session_id = ?
            ''', (session_id,))
    
    def cleanup_invalid_sessions(self):
        """시간대 문제가 있는 기존 세션들 정리"""
        with sqlite3.connect(self.db_path) as conn:
            # 모든 활성 세션을 가져와서 하나씩 검증
            cursor = conn.execute('''
                SELECT session_id, expires_at 
                FROM user_sessions 
                WHERE is_active = 1
            ''')
            
            invalid_sessions = []
            
            for session_id, expires_at in cursor.fetchall():
                try:
                    # 날짜 파싱 테스트
                    expires_at_dt = datetime.datetime.fromisoformat(expires_at)
                    
                    # timezone 정보가 있는 경우 문제가 될 수 있음
                    if '+' in expires_at or 'T' in expires_at and expires_at.endswith('Z'):
                        invalid_sessions.append(session_id)
                        
                except Exception:
                    # 파싱 실패한 세션도 무효화
                    invalid_sessions.append(session_id)
            
            # 문제가 있는 세션들 무효화
            for session_id in invalid_sessions:
                conn.execute('''
                    UPDATE user_sessions 
                    SET is_active = 0 
                    WHERE session_id = ?
                ''', (session_id,))
                
            if invalid_sessions:
                print(f"Cleaned up {len(invalid_sessions)} invalid sessions")
    
    def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE expires_at < CURRENT_TIMESTAMP
            ''')
    
    # =============================================================================
    # 사용자 설정 관리
    # =============================================================================
    
    def save_user_preference(self, username: str, key: str, value: Any):
        """사용자 설정 저장"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_preferences (username, preference_key, preference_value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (username, key, value_str))
    
    def get_user_preference(self, username: str, key: str, default=None):
        """사용자 설정 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT preference_value FROM user_preferences
                WHERE username = ? AND preference_key = ?
            ''', (username, key))
            
            result = cursor.fetchone()
            if not result:
                return default
            
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
    
    def get_all_user_preferences(self, username: str) -> Dict[str, Any]:
        """사용자의 모든 설정 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT preference_key, preference_value FROM user_preferences
                WHERE username = ?
            ''', (username,))
            
            preferences = {}
            for key, value in cursor.fetchall():
                try:
                    preferences[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    preferences[key] = value
            
            return preferences
    
    # =============================================================================
    # 분석 리포트 관리 메서드 (기존 ReportHistoryManager 기능)
    # =============================================================================
    
    def create_analysis_session(self, username: str, ticker: str, config: Dict = None, 
                               analysis_date = None) -> str:
        """새로운 분석 세션 생성"""
        session_id = str(uuid.uuid4())
        
        # analysis_date 처리 - 문자열, datetime, None 모두 처리
        if analysis_date is None:
            analysis_date_iso = datetime.datetime.now().isoformat()
        elif isinstance(analysis_date, str):
            # 이미 문자열인 경우 (YYYY-MM-DD 형식)
            try:
                # 날짜 문자열을 datetime으로 파싱 후 다시 ISO 형식으로
                parsed_date = datetime.datetime.strptime(analysis_date, "%Y-%m-%d")
                analysis_date_iso = parsed_date.isoformat()
            except ValueError:
                # 이미 ISO 형식인 경우 그대로 사용
                analysis_date_iso = analysis_date
        else:
            # datetime 객체인 경우
            analysis_date_iso = analysis_date.isoformat()
        
        config_json = json.dumps(config) if config else None
        
        print(f"[DB] Creating analysis session - User: {username}, Ticker: {ticker}, Date: {analysis_date_iso[:10]}, Session ID: {session_id[:8]}...")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO analysis_sessions (session_id, username, ticker, analysis_date, status, config_snapshot)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, username, ticker, analysis_date_iso, 'running', config_json))
        
        print(f"[DB] ✅ Analysis session created successfully: {session_id[:8]}")
        return session_id
    
    def save_report_section(self, session_id: str, section_type: str, agent_name: str, content: str):
        """리포트 섹션 저장"""
        print(f"[DB] Saving report section - Session: {session_id[:8]}, Type: {section_type}, Agent: {agent_name}, Content length: {len(content)}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO report_sections (session_id, section_type, agent_name, content)
                VALUES (?, ?, ?, ?)
            ''', (session_id, section_type, agent_name, content))
        
        print(f"[DB] ✅ Report section saved: {section_type}")
    
    def update_agent_status(self, session_id: str, agent_name: str, status: str, 
                           started_at: datetime.datetime = None, 
                           completed_at: datetime.datetime = None,
                           error_message: str = None):
        """에이전트 실행 상태 업데이트"""
        execution_time = None
        if started_at and completed_at:
            execution_time = (completed_at - started_at).total_seconds()
        
        started_at_iso = started_at.isoformat() if started_at else None
        completed_at_iso = completed_at.isoformat() if completed_at else None
        
        with sqlite3.connect(self.db_path) as conn:
            # 기존 레코드 확인
            cursor = conn.execute('''
                SELECT id FROM agent_executions 
                WHERE session_id = ? AND agent_name = ?
            ''', (session_id, agent_name))
            
            existing = cursor.fetchone()
            
            if existing:
                # 업데이트
                conn.execute('''
                    UPDATE agent_executions 
                    SET status = ?, started_at = COALESCE(?, started_at), 
                        completed_at = ?, execution_time_seconds = ?, error_message = ?
                    WHERE session_id = ? AND agent_name = ?
                ''', (status, started_at_iso, completed_at_iso, execution_time, error_message, session_id, agent_name))
            else:
                # 새로 삽입
                conn.execute('''
                    INSERT INTO agent_executions (session_id, agent_name, status, started_at, completed_at, execution_time_seconds, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session_id, agent_name, status, started_at_iso, completed_at_iso, execution_time, error_message))
    
    def complete_analysis_session(self, session_id: str, final_decision: str = None, confidence_score: float = None, execution_time_seconds: float = None):
        """분석 세션 완료 처리"""
        print(f"[DB] Completing analysis session - Session: {session_id[:8]}, Decision: {final_decision}, Confidence: {confidence_score}, Duration: {execution_time_seconds}s")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE analysis_sessions 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
                    final_decision = ?, confidence_score = ?, execution_time_seconds = ?
                WHERE session_id = ?
            ''', (final_decision, confidence_score, execution_time_seconds, session_id))
        
        print(f"[DB] ✅ Analysis session completed: {session_id[:8]}")
    
    def get_user_analysis_sessions(self, username: str, ticker: str = None, limit: int = 50) -> List[Dict]:
        """사용자의 분석 세션 목록 조회"""
        print(f"[DB] Querying user analysis sessions - User: {username}, Ticker: {ticker}, Limit: {limit}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if ticker:
                cursor = conn.execute('''
                    SELECT * FROM analysis_sessions 
                    WHERE username = ? AND ticker = ?
                    ORDER BY analysis_date DESC, created_at DESC
                    LIMIT ?
                ''', (username, ticker, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM analysis_sessions 
                    WHERE username = ?
                    ORDER BY analysis_date DESC, created_at DESC
                    LIMIT ?
                ''', (username, limit))
            
            results = [dict(row) for row in cursor.fetchall()]
            print(f"[DB] ✅ Found {len(results)} analysis sessions for user {username}")
            return results
    
    def get_analysis_sessions(self, ticker: str = None, limit: int = 50) -> List[Dict]:
        """모든 분석 세션 목록 조회 (관리자용)"""
        print(f"[DB] Querying all analysis sessions - Ticker: {ticker}, Limit: {limit}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if ticker:
                cursor = conn.execute('''
                    SELECT * FROM analysis_sessions 
                    WHERE ticker = ?
                    ORDER BY analysis_date DESC, created_at DESC
                    LIMIT ?
                ''', (ticker, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM analysis_sessions 
                    ORDER BY analysis_date DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            results = [dict(row) for row in cursor.fetchall()]
            print(f"[DB] ✅ Found {len(results)} total analysis sessions")
            return results
    
    def get_session_report(self, session_id: str) -> Dict[str, Any]:
        """특정 세션의 전체 리포트 조회"""
        print(f"[DB] Loading session report - Session: {session_id[:8]}")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 세션 정보
            session_cursor = conn.execute('''
                SELECT * FROM analysis_sessions WHERE session_id = ?
            ''', (session_id,))
            session_result = session_cursor.fetchone()
            
            if not session_result:
                print(f"[DB] ❌ Session not found: {session_id[:8]}")
                raise ValueError(f"Session {session_id} not found")
            
            session_info = dict(session_result)
            
            # 리포트 섹션들
            sections_cursor = conn.execute('''
                SELECT section_type, agent_name, content, created_at
                FROM report_sections 
                WHERE session_id = ?
                ORDER BY created_at ASC
            ''', (session_id,))
            sections = [dict(row) for row in sections_cursor.fetchall()]
            
            # 에이전트 실행 정보
            agents_cursor = conn.execute('''
                SELECT agent_name, status, started_at, completed_at, execution_time_seconds, error_message
                FROM agent_executions 
                WHERE session_id = ?
                ORDER BY started_at ASC
            ''', (session_id,))
            agents = [dict(row) for row in agents_cursor.fetchall()]
            
            print(f"[DB] ✅ Loaded session report: {len(sections)} sections, {len(agents)} agents")
            return {
                'session_info': session_info,
                'report_sections': sections,
                'agent_executions': agents
            }
    
    def get_user_ticker_summary(self, username: str, ticker: str, days: int = 30) -> Dict[str, Any]:
        """사용자의 특정 티커 분석 요약"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 최근 분석 수
            total_cursor = conn.execute('''
                SELECT COUNT(*) as total FROM analysis_sessions 
                WHERE username = ? AND ticker = ? AND analysis_date >= ?
            ''', (username, ticker, cutoff_date.isoformat()))
            total_analyses = total_cursor.fetchone()['total']
            
            # 결정 분포
            decisions_cursor = conn.execute('''
                SELECT final_decision, COUNT(*) as count FROM analysis_sessions 
                WHERE username = ? AND ticker = ? AND analysis_date >= ? AND final_decision IS NOT NULL
                GROUP BY final_decision
            ''', (username, ticker, cutoff_date.isoformat()))
            decisions = {row['final_decision']: row['count'] for row in decisions_cursor.fetchall()}
            
            # 평균 신뢰도
            confidence_cursor = conn.execute('''
                SELECT AVG(confidence_score) as avg_confidence FROM analysis_sessions 
                WHERE username = ? AND ticker = ? AND analysis_date >= ? AND confidence_score IS NOT NULL
            ''', (username, ticker, cutoff_date.isoformat()))
            avg_confidence = confidence_cursor.fetchone()['avg_confidence']
            
            return {
                'username': username,
                'ticker': ticker,
                'period_days': days,
                'total_analyses': total_analyses,
                'decision_distribution': decisions,
                'average_confidence': avg_confidence
            }
    
    def export_session_to_json(self, session_id: str) -> str:
        """세션 데이터를 JSON으로 내보내기"""
        report_data = self.get_session_report(session_id)
        return json.dumps(report_data, default=str, indent=2, ensure_ascii=False)
    
    def delete_analysis_session(self, session_id: str, username: str = None) -> bool:
        """분석 세션 삭제 (사용자 확인 포함)"""
        print(f"[DB] Deleting analysis session - Session: {session_id[:8]}, User: {username}")
        
        with sqlite3.connect(self.db_path) as conn:
            # 세션 존재 및 권한 확인
            if username:
                cursor = conn.execute('''
                    SELECT username FROM analysis_sessions 
                    WHERE session_id = ?
                ''', (session_id,))
                result = cursor.fetchone()
                
                if not result:
                    print(f"[DB] ❌ Session not found: {session_id[:8]}")
                    return False
                
                if result[0] != username:
                    print(f"[DB] ❌ Permission denied: {username} cannot delete session owned by {result[0]}")
                    return False
            
            # 연관된 데이터 모두 삭제 (순서 중요: 외래 키 제약 때문에)
            # 1. 에이전트 실행 로그 삭제
            conn.execute('DELETE FROM agent_executions WHERE session_id = ?', (session_id,))
            
            # 2. 리포트 섹션 삭제
            conn.execute('DELETE FROM report_sections WHERE session_id = ?', (session_id,))
            
            # 3. 분석 세션 삭제
            result = conn.execute('DELETE FROM analysis_sessions WHERE session_id = ?', (session_id,))
            
            if result.rowcount > 0:
                print(f"[DB] ✅ Analysis session deleted successfully: {session_id[:8]}")
                return True
            else:
                print(f"[DB] ❌ Failed to delete session: {session_id[:8]}")
                return False
    
    def cleanup_old_sessions(self, days_to_keep: int = 90):
        """오래된 세션 정리"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        cutoff_iso = cutoff_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 관련 테이블에서 모두 삭제
            conn.execute('''
                DELETE FROM agent_executions 
                WHERE session_id IN (
                    SELECT session_id FROM analysis_sessions WHERE created_at < ?
                )
            ''', (cutoff_iso,))
            
            conn.execute('''
                DELETE FROM report_sections 
                WHERE session_id IN (
                    SELECT session_id FROM analysis_sessions WHERE created_at < ?
                )
            ''', (cutoff_iso,))
            
            conn.execute('''
                DELETE FROM analysis_sessions WHERE created_at < ?
            ''', (cutoff_iso,))
            
            conn.commit()
    
    # =============================================================================
    # 관리자용 메서드
    # =============================================================================
    
    def get_user_stats(self) -> Dict[str, Any]:
        """사용자 통계"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 전체 사용자 수
            total_users = conn.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1').fetchone()['count']
            
            # 활성 세션 수
            active_sessions = conn.execute('''
                SELECT COUNT(*) as count FROM user_sessions 
                WHERE is_active = 1 AND expires_at > CURRENT_TIMESTAMP
            ''').fetchone()['count']
            
            # 오늘 분석 수
            today = datetime.date.today().isoformat()
            today_analyses = conn.execute('''
                SELECT COUNT(*) as count FROM analysis_sessions 
                WHERE DATE(created_at) = ?
            ''', (today,)).fetchone()['count']
            
            return {
                'total_users': total_users,
                'active_sessions': active_sessions,
                'today_analyses': today_analyses
            }