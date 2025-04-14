import cv2
import time

def test_camera():
    # Thử camera index 0 (webcam mặc định)
    print("Đang kiểm tra camera...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Không thể mở camera!")
        return
        
    # Đặt buffer size
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Đọc và hiển thị frame trong 10 giây
    start_time = time.time()
    frame_count = 0
    
    print("Camera đã mở. Đang test trong 10 giây...")
    
    while (time.time() - start_time) < 10:
        ret, frame = cap.read()
        if not ret:
            print("Không thể đọc frame!")
            break
            
        frame_count += 1
        cv2.imshow('Camera Test', frame)
        
        # Hiển thị FPS
        fps = frame_count / (time.time() - start_time)
        print(f"\rFPS: {fps:.2f}", end="")
        
        # Thoát nếu nhấn ESC
        if cv2.waitKey(1) == 27:
            break
    
    # Thống kê
    print(f"\n\nKết quả test:")
    print(f"- Tổng số frame: {frame_count}")
    print(f"- FPS trung bình: {frame_count/(time.time()-start_time):.2f}")
    print(f"- Độ phân giải: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    
    # Giải phóng camera
    cap.release()
    cv2.destroyAllWindows()
    print("\nĐã đóng camera")

if __name__ == "__main__":
    test_camera() 