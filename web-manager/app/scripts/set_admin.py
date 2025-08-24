import configparser
import os
from supabase import create_client, Client

# --- 설정 ---
# 관리자 권한을 부여할 사용자의 이메일 주소를 아래에 입력하세요.
ADMIN_EMAIL = "ksm46351@gmail.com" 
# --- 설정 ---

def set_admin_by_email():
    """
    manager_config.ini 파일에서 설정을 읽고,
    지정된 이메일 주소를 가진 사용자에게 관리자 권한을 부여합니다.
    """
    if not ADMIN_EMAIL or ADMIN_EMAIL == "admin@example.com":
        print("오류: 스크립트 상단의 ADMIN_EMAIL 변수를 실제 관리자 이메일 주소로 변경해주세요.")
        return

    try:
        # 스크립트 파일의 절대 경로를 기준으로 설정 파일의 경로를 계산합니다.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, '..', 'core', 'manager_config.ini')
        config_path = os.path.normpath(config_path)
        
        if not os.path.exists(config_path):
            print(f"오류: 설정 파일을 찾을 수 없습니다. 계산된 경로: {config_path}")
            return

        # 설정 파일 읽기
        config = configparser.ConfigParser()
        config.read(config_path)

        # Supabase 정보 추출
        supabase_url = config['SUPABASE']['URL']
        supabase_service_key = config['SUPABASE']['SERVICE_KEY']

        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase URL 및 SERVICE_KEY가 설정 파일에 필요합니다.")

        print("Supabase 클라이언트를 초기화합니다...")
        supabase: Client = create_client(supabase_url, supabase_service_key)

        # 사용자 목록 가져오기
        print("모든 사용자 목록을 조회합니다...")
        # supabase-py v2부터 list_users()는 사용자 리스트를 직접 반환합니다.
        users_list = supabase.auth.admin.list_users()

        if not users_list:
            print("등록된 사용자가 없습니다.")
            return

        # 이메일 주소로 대상 사용자 찾기
        # .users 속성 없이 리스트에서 직접 검색합니다.
        target_user = next((user for user in users_list if user.email == ADMIN_EMAIL), None)
        
        if not target_user:
            print(f"오류: 이메일 '{ADMIN_EMAIL}'을(를) 가진 사용자를 찾을 수 없습니다.")
            return
            
        print(f"대상 사용자를 찾았습니다: {target_user.email} (ID: {target_user.id})")

        # 해당 사용자의 메타데이터 업데이트
        current_metadata = target_user.user_metadata or {}
        
        if current_metadata.get("role") == "admin":
            print(f"사용자 '{target_user.email}'는 이미 관리자입니다.")
            return

        current_metadata['role'] = 'admin'
        
        print(f"사용자 '{target_user.email}'에게 관리자 권한을 부여합니다...")
        update_response = supabase.auth.admin.update_user_by_id(
            uid=target_user.id,
            attributes={"user_metadata": current_metadata}
        )
        
        print("\n--- 성공 ---")
        print(f"사용자 '{update_response.user.email}'에게 성공적으로 관리자 권한을 부여했습니다.")
        print("업데이트된 메타데이터:", update_response.user.user_metadata)

    except FileNotFoundError:
        print(f"오류: 설정 파일을 찾을 수 없습니다. 경로를 확인하세요: {config_path}")
    except KeyError as e:
        print(f"오류: 설정 파일에 필요한 키가 없습니다: {e}")
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    set_admin_by_email()
