from ultralytics import YOLO

# Load a pretrained YOLO26 nano model
model = YOLO("yolov8n.pt")

# Run inference on an image
results = model("dog.png")

results[0].show()

from ultralytics import YOLO

# Initialize a YOLO-World model
model = YOLO("yolov8l-world.pt")  # or choose yolov8m/l-world.pt

# Define custom classes
model.set_classes(["person", "bus", "dog"])

# Execute prediction for specified categories on an image
results = model.predict("dog.png")

# Show results
results[0].show()