import cv2
import math
import pickle
import base64
import json
import os
import face_recognition
import numpy as np
from sklearn import neighbors
from DatabaseHooking import connect_db

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

db_username = base64.b64decode(config.get("db_username", "")).decode("utf-8")
db_password = base64.b64decode(config.get("db_password", "")).decode("utf-8")
db_host = config.get("db_host", "localhost")

def train_from_db(cursor, model_save_path=None, n_neighbors=None, knn_algo='ball_tree', verbose=False):
    X = []
    y = []
    query = "SELECT HoVaTen, ImagePath FROM Students"
    cursor.execute(query)
    results = cursor.fetchall()
    if verbose:
        print(f"Đã lấy được {len(results)} mẫu từ CSDL.")
    for record in results:
        name, image_path = record
        if not os.path.exists(image_path):
            if verbose:
                print(f"Không tìm thấy file: {image_path}")
            continue
        
        # Đọc và xử lý ảnh
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        
        # Kiểm tra có khuôn mặt không
        if len(face_locations) == 0:
            if verbose:
                print(f"Không phát hiện khuôn mặt trong ảnh: {image_path}")
            continue
            
        # Xử lý tất cả khuôn mặt tìm thấy
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        # Thêm encoding cho mỗi khuôn mặt
        for encoding in face_encodings:
            X.append(encoding)
            y.append(name)
            if verbose:
                print(f"Đã thêm {len(face_encodings)} khuôn mặt cho {name}")
    
    if len(X) == 0:
        raise Exception("Không có dữ liệu huấn luyện hợp lệ.")
        
    if n_neighbors is None:
        n_neighbors = int(round(math.sqrt(len(X))))
        if verbose:
            print("Chọn n_neighbors tự động:", n_neighbors)
            
    # Huấn luyện model
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm=knn_algo, weights='distance')
    knn_clf.fit(X, y)
    
    # Lưu model
    if model_save_path is not None:
        with open(model_save_path, 'wb') as f:
            pickle.dump(knn_clf, f)
            
    if verbose:
        print(f"Đã train xong model với {len(X)} khuôn mặt từ {len(set(y))} người")
    
    return knn_clf

def face_loop(cnx, cursor, camera_source=0):
    cap = None
    try:
        cap = cv2.VideoCapture(camera_source)
        if not cap.isOpened():
            raise Exception("Không thể mở camera")
            
        # Khởi tạo model
        knn_model_path = "trained_knn_model.clf"
        if not os.path.exists(knn_model_path):
            print("Huấn luyện model mới...")
            knn_clf = train_from_db(cursor, model_save_path=knn_model_path, verbose=True)
        else:
            with open(knn_model_path, 'rb') as f:
                knn_clf = pickle.load(f)
        
        print("Đã khởi động camera. Nhấn ESC để thoát.")
        
        # Dictionary để theo dõi điểm danh
        attendance_buffer = {}
        attendance_threshold = 5  # Số frame liên tiếp cần để xác nhận
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Lỗi khi đọc frame từ camera")
                break
                
            # Nhận diện khuôn mặt
            try:
                predictions = predict(frame, knn_clf=knn_clf)
                
                # Xử lý điểm danh
                current_names = set()
                for name, _ in predictions:
                    if name != "unknown":
                        current_names.add(name)
                        if name not in attendance_buffer:
                            attendance_buffer[name] = 1
                        else:
                            attendance_buffer[name] += 1
                            
                        if attendance_buffer[name] >= attendance_threshold:
                            cursor.execute("SELECT DiemDanhStatus FROM Students WHERE HoVaTen = %s", (name,))
                            current_status = cursor.fetchone()
                            
                            if current_status and current_status[0] == '❌':
                                cursor.execute("""
                                    UPDATE Students 
                                    SET DiemDanhStatus = '✓', 
                                        ThoiGianDiemDanh = NOW() 
                                    WHERE HoVaTen = %s
                                """, (name,))
                                cnx.commit()
                                print(f"Đã điểm danh thành công: {name}")
                
                # Giảm giá trị đếm cho những người không xuất hiện
                for name in list(attendance_buffer.keys()):
                    if name not in current_names:
                        attendance_buffer[name] = max(0, attendance_buffer[name] - 1)
                        if attendance_buffer[name] == 0:
                            del attendance_buffer[name]
                
                frame = show_labels(frame, predictions)
                
            except Exception as e:
                print(f"Lỗi nhận diện: {str(e)}")
                continue
            
            cv2.imshow('Face Recognition', frame)
            
            if cv2.waitKey(1) & 0xFF == 27:  # ESC
                print("Đã nhấn ESC. Thoát khỏi chương trình.")
                break
                
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Đã đóng camera và kết thúc chương trình.")

def predict(frame, knn_clf=None, model_path=None, distance_threshold=0.5):
    """Nhận diện tất cả khuôn mặt trong frame"""
    if knn_clf is None and model_path is None:
        raise Exception("Phải cung cấp knn classifier.")
        
    if knn_clf is None:
        with open(model_path, 'rb') as f:
            knn_clf = pickle.load(f)
            
    # Phát hiện vị trí các khuôn mặt
    face_locations = face_recognition.face_locations(frame)
    if len(face_locations) == 0:
        return []
        
    # Tính toán encoding cho tất cả khuôn mặt
    face_encodings = face_recognition.face_encodings(frame, face_locations)
    
    # Dự đoán và tính khoảng cách cho mỗi khuôn mặt
    closest_distances = knn_clf.kneighbors(face_encodings, n_neighbors=1)
    are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(face_locations))]
    
    # Dự đoán tên cho mỗi khuôn mặt
    predictions = []
    for i, (pred, loc, is_match) in enumerate(zip(knn_clf.predict(face_encodings), face_locations, are_matches)):
        if is_match:
            predictions.append((pred, loc))
        else:
            predictions.append(("unknown", loc))
            
    return predictions

def show_labels(frame, predictions):
    for name, (top, right, bottom, left) in predictions:
        # Vẽ khung xanh quanh khuôn mặt
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        
        # Hiển thị tên phía dưới khung
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
    return frame

def main(cnx=None, cursor=None, camera_source=0):
    """Hàm chính để chạy nhận diện khuôn mặt"""
    try:
        if cnx is None or cursor is None:
            cnx, cursor = connect_db(db_username, db_password, db_host)
            if cnx is None or cursor is None:
                raise Exception("Lỗi kết nối CSDL MySQL!")

        knn_model_path = "trained_knn_model.clf"
        if os.path.exists(knn_model_path):
            os.remove(knn_model_path)
            print("Đã xóa model cũ.")
        
        print("Đang train model mới từ CSDL...")
        train_from_db(cursor, model_save_path=knn_model_path, verbose=True)
        
        face_loop(cnx, cursor, camera_source)
        return True
        
    except Exception as e:
        print(f"Lỗi trong quá trình chạy: {str(e)}")
        return False

if __name__ == "__main__":
    main()