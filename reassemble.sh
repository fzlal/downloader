#!/bin/bash
# اسکریپت برای چسباندن تکه‌ها و لود کردن تصاویر داکر

echo "🔧 Reassembling Docker images from split parts..."

for IMAGE_DIR in images/split/*/; do
  if [ -d "$IMAGE_DIR" ]; then
    BASENAME=$(basename "$IMAGE_DIR")
    echo "📦 Reassembling: $BASENAME"
    
    # چسباندن تکه‌ها به یک فایل کامل
    cat "$IMAGE_DIR"part_* > "${BASENAME}.tar"
    
    # لود کردن به داکر
    echo "  Loading into Docker..."
    docker load < "${BASENAME}.tar"
    
    # پاک کردن فایل tar موقت
    rm "${BASENAME}.tar"
    echo "  ✅ Done for $BASENAME"
  fi
done

echo "🎉 All images have been loaded successfully!"
