import cv2
#rtmp://campfc.mskims.com/live/123456
# Replace this with your RTMP URL
rtmp_url = "rtmp://campfc.mskims.com:1935/LiveApp/stream1"

# Open the RTMP stream
cap = cv2.VideoCapture(rtmp_url, cv2.CAP_FFMPEG)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1180)
if not cap.isOpened():
    print("Failed to open RTMP stream")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    cv2.imshow("RTMP Stream", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()