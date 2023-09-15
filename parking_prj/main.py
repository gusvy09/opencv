from flask import Flask, redirect, render_template, Response, request, jsonify, url_for
from time import sleep
import requests
import function as fn
import cv2
import cvzone
import math
from ultralytics import YOLO
from datetime import datetime
import time

addcarno = ""
# YOLO 학습 데이터
model = YOLO("best.pt")
classNames = ["plate"]


app = Flask(__name__)
capture = cv2.VideoCapture(cv2.CAP_DSHOW + 0)  # 웹캠으로부터 비디오 캡처 객체 생성
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # 캡처된 비디오의 폭 설정
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # 캡처된 비디오의 높이 설정


# 웹캠을 인코딩 -> 바이트로 변환 후 프레임을 클라이언트에 반환
def GenerateFrames():
    while True:
        sleep(0.1)  # 프레임 생성 간격을 잠시 지연시킵니다.
        ref, frame = capture.read()  # 비디오 프레임을 읽어옵니다.
        cv2.rectangle(
            frame,
            pt1=(40, 200),
            pt2=(600, 400),
            color=(0, 255, 0),
            thickness=2,
        )
        results = model(frame, stream=True)
        if not ref:  # 비디오 프레임을 제대로 읽어오지 못했다면 반복문을 종료합니다.
            break
        else:
            bcheck = False
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Bounding Box
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    # cv2.rectangle(img,(x1,y1),(x2,y2),(255,0,255),3)
                    w, h = x2 - x1, y2 - y1
                    # end_frame = new_frame[y1 - 20 : y2 + 20, x1 - 20 : x2 + 20]
                    cvzone.cornerRect(frame, (x1, y1, w, h))
                    # Confidence
                    conf = math.ceil((box.conf[0] * 100)) / 100
                    # Class Name
                    cls = int(box.cls[0])

                    cvzone.putTextRect(
                        frame,
                        f"number : {conf}",
                        (max(0, x1), max(35, y1)),
                        scale=1,
                        thickness=1,
                    )
                    # 감지조건
                    # 초록색 네모박스안에 번호판이 들어가면서, 인식률이 0.5이상인 경우
                    if (x1 > 40 and x2 < 600 and y1 > 200 and y2 < 400) and conf > 0.5:
                        bcheck = fn.search_str(frame, x1, x2, y1, y2)
                        # print(no)
                    if bcheck:
                        cv2.putText(
                            frame,
                            "open",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            2.5,
                            (0, 0, 255),
                            2,
                        )

            ref, buffer = cv2.imencode(".jpg", frame)  # JPEG 형식으로 이미지를 인코딩합니다.
            frame = buffer.tobytes()  # 인코딩된 이미지를 바이트 스트림으로 변환합니다.

            # multipart/x-mixed-replace 포맷으로 비디오 프레임을 클라이언트에게 반환합니다.
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            if bcheck:
                # 2초 동안 멈추기
                time.sleep(2)
                # bcheck를 다시 False로 설정하여 웹캠을 정상적으로 동작하도록 함
                bcheck = False


# 기본 페이지, 사용중인 자리를 return받아서 html 업데이트
@app.route("/")
def Index():
    pzone = fn.pzone()  # 사용중인 주차 자리
    data = {"zone": pzone}
    return render_template("index.html", data=data)  # index.html 파일을 렌더링하여 반환합니다.


# 등록차량 멤버 html, 등록되어 있는 차들을 return
@app.route("/member", methods=["GET", "POST"])
def park_member():
    car_no = fn.car_no()
    data = {"car_no": car_no}
    return render_template("member.html", data=data)


# 정보처리 및 전달(주차자리 입력, 삭제)
@app.route("/server_endpoint", methods=["POST"])
def server_endpoint():
    try:
        data = request.get_json()
        datalist = data.split()
        # 주차선 색 바꾸기
        if len(datalist) == 2:
            try:
                if datalist[1] == "red":  # pzone에서 빼기
                    fn.delete_zone(datalist[0])
                else:  # pzone에 넣기
                    fn.add_zone(datalist[0])

            except Exception as e:
                return jsonify({"error": str(e)})
            finally:
                result_data = {"message": "데이터 처리완료"}
                return jsonify(result_data)
        # 입차확인(차량번호 체크), 차단봉 열기
        else:
            pass
    except Exception as e:
        return jsonify({"error": str(e)})


# streaming video기능
@app.route("/stream")
def Stream():
    # GenerateFrames 함수를 통해 비디오 프레임을 클라이언트에게 실시간으로 반환합니다.
    return Response(
        GenerateFrames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# 정보처리 및 전달(차량등록 팝업에서 보냄) return 없으면 안됨
# data = "'차량번호' '버튼기능(add,del)' '핸디여부(true,false)'"
# add버튼으로 들어오면 결제창 이동해야됨
@app.route("/m_server_endpoint", methods=["POST"])
def m_server_endpoint():
    # 동작을 실행했으면 True반환, 새로고침 아니면 False 반환 아무동작x
    exist = True
    try:
        # 차 넘버를 받아와서 등록되어있는 차넘버들과 비교
        data = request.get_json()
        list_data = data.split()
        list_carno = fn.car_no()
        print(list_data)
        # 등록버튼눌렸을 경우
        if list_data[1] == "add":
            # list_carno -> 튜플로 리턴([차량번호],[핸디여부])
            if list_data[0] in list_carno[0]:
                exist = False
                result_data = {
                    "message": "데이터 처리완료",
                    "work": exist,
                }  # false로 반환(아무작업 안 함)
                return jsonify(result_data)
            # 등록
            else:
                global addcarno
                addcarno = list_data[0]
                # fn.add_car_no(list_data[0], list_data[2])
                result_data = {
                    "message": "데이터 처리완료",
                    "work": exist,
                }  # true로 반환(등록 완료)
                return jsonify(result_data)
        # 삭제버튼
        else:
            if list_data[0] not in list_carno[0]:  # 등록안되어 있는 차
                exist = False
                result_data = {
                    "message": "데이터 처리완료",
                    "work": exist,
                }  # false로 반환(아무작업 안 함)
                return jsonify(result_data)
            else:
                fn.delete_car_no(list_data[0])
                result_data = {"message": "데이터 처리완료", "work": exist}  # true로 반환(삭제완료)
                return jsonify(result_data)
    except Exception as e:
        return jsonify({"error": str(e)})


# 결제 성공시 기본 페이지로 이동
@app.route("/payment-success", methods=["GET"])
def payment_success():
    # 데이터베이스에 결제 정보 추가
    fn.add_car_no(addcarno, False)
    # SQLAlchemy 또는 다른 데이터베이스 ORM을 사용하여 데이터베이스에 정보를 추가하세요.
    # 결제 성공 메시지를 사용자에게 표시
    pzone = fn.pzone()  # 사용중인 주차 자리
    data = {"zone": pzone}
    return render_template("index.html", data=data)


# 결제 페이지로 이동
@app.route("/kakaopay/pay", methods=["POST"])
def kakaopay_payment():
    # 카카오페이 결제 요청을 생성
    SERVICE_APP_ADMIN_KEY = "c929cb871d0ce7147e0e70dfb97508aa"
    payload = {
        "cid": "TC0ONETIME",  # 가맹점 CID
        "partner_order_id": "order123",  # 가맹점 주문번호
        "partner_user_id": "user123",  # 가맹점 회원 ID
        "item_name": "주차권(한달)",  # 상품명
        "quantity": 1,  # 수량
        "total_amount": 50000,  # 총 결제 금액
        "tax_free_amount": 0,  # 비과세 금액
        "approval_url": "http://localhost:5000/payment-success",  # 결제 성공 시 리다이렉션할 URL
        "fail_url": "http://localhost:5000/",  # 결제 실패 시 리다이렉션할 URL
        "cancel_url": "http://localhost:5000/",  # 결제 취소 시 리다이렉션할 URL
    }

    headers = {
        "Authorization": "KakaoAK {}".format(
            SERVICE_APP_ADMIN_KEY
        ),  # 카카오페이 API에 접근하기 위한 인증 토큰
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    }

    # 카카오페이 결제 요청을 보냄
    response = requests.post(
        "https://kapi.kakao.com/v1/payment/ready", data=payload, headers=headers
    )

    # 응답 처리 로직을 작성하세요.
    if response.status_code == 200:
        result = response.json()
        # 결제 준비 요청이 성공하면 사용자를 카카오페이 결제 페이지로 리다이렉트합니다.
        print("ok")
        return redirect(result["next_redirect_pc_url"])
    else:
        # 오류 처리
        return "카카오페이 결제 요청에 실패했습니다."


if __name__ == "__main__":
    # 라즈베리파이의 IP 번호와 포트 번호를 지정하여 Flask 앱을 실행합니다.
    # host = 192.168.0.29:5000 , 기본포트 5000
    app.run(host="0.0.0.0")
