# db접근, 기능구현
import pymysql
import re

# opencv관련
import cv2
import pytesseract


# db연결하는 함수
def connect_db():
    try:
        connect_db = pymysql.connect(
            user="hp",
            password="1234",
            host="127.0.0.1",
            db="mobledb",
            charset="utf8",
        )
        return connect_db
    except pymysql.Error as e:
        print("error : " + str(e))
        return None


# 사용중인 자리 출력 data[0][0]에 위치가 나옴
# list로 반환
def pzone():
    list_park_no = []
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "SELECT * FROM parkingzone"
    cursor.execute(sql)
    data = cursor.fetchall()
    for i in range(len(data)):
        list_park_no.append(data[i][0])
    # print(list_park_no)
    sensor_db.close()
    return list_park_no


# 등록차량 리턴 (list로 반환)
def car_no():
    list_car_no = []
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "SELECT * FROM car_info"
    cursor.execute(sql)
    data = cursor.fetchall()
    for i in range(len(data)):
        list_car_no.append(data[i][0])
    # print(list_car_no)
    sensor_db.close()
    return list_car_no


def add_zone(park_zone):  # 사용할 주차라인을 db에 추가
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "insert into parkingzone(pzone) values('%s')" % park_zone
    try:
        cursor.execute(sql)
        sensor_db.commit()
    except Exception as e:
        sensor_db.rollback()
        print("error : ", str(e))
    finally:
        sensor_db.close()


def delete_zone(park_zone):  # 빠져나간 주차라인을 db에서 삭제
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "delete from parkingzone where pzone='%s'" % park_zone
    try:
        cursor.execute(sql)
        sensor_db.commit()
    except Exception as e:
        sensor_db.rollback()
        print("error : ", str(e))
    finally:
        sensor_db.close()


def add_car_no(car_no, bcheck):  # 차 넘버 sql에 저장
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "insert into car_info(car_num) values('%s')" % (car_no)
    cursor.execute(sql)
    sensor_db.commit()
    sensor_db.close()


def delete_car_no(car_no):  # 차 넘버 sql에서 지우기
    sensor_db = connect_db()
    cursor = sensor_db.cursor()
    sql = "delete from car_info where car_num = '%s'" % car_no
    cursor.execute(sql)
    sensor_db.commit()
    sensor_db.close()


######################################################################
###########################opencv관련코드##############################
def search_str(frame, x1, x2, y1, y2):
    # list_car_no = car_no() #등록차량 받기
    frame = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # 가우시안 블러 -> 노이즈 줄이기
    img_blurred = cv2.GaussianBlur(gray, ksize=(5, 5), sigmaX=0)
    # 스레시 홀드 -> 이미지 구별 쉽게 만들기(0과 255로 바꿈)
    img_thresh = cv2.adaptiveThreshold(
        img_blurred,
        maxValue=255.0,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY_INV,
        blockSize=19,
        C=9,
    )
    # 글자추출
    result = result = pytesseract.image_to_string(img_thresh, lang="eng")
    # 번호판 앞 두자리, 뒤 네자리로 변환
    result = re.sub(r"[^0-9]", "", result)
    if len(result) > 5:
        print("result : ", result)
        p = re.compile("^")
        answer = result[:2] + result[-4:]
        list_no = car_no()
        # 번호판 앞 뒤
        list_no = remove_korean_from_list(list_no)
        print(list_no)
        # 차량번호 앞 두자리, 뒤 네자리만 비교후 같으면
        # true return, 같지 않으면 false return
        for i in list_no:
            print(i[:2])
            print(i[-4:])
            if answer in i[:2] + i[-4:]:
                print(i[:2] + i[-4:])
                print("=======")
                print(answer)
                print("ㄷㄷ : " + answer)
                print("=======")
                print("있음")
                return True
            else:
                pass
        return False


# 번호판의 한글 제거
def remove_korean_from_list(input_list):
    # 정규식 패턴으로 한글을 찾아 제거합니다.
    pattern = re.compile("[ㄱ-ㅎㅏ-ㅣ가-힣]+")

    # 각 문자열에 대해 한글을 제거한 새로운 리스트를 생성합니다.
    result_list = [pattern.sub("", text) for text in input_list]

    return result_list
