# Customer Video Playback - User Flow

## 🎬 Feature Overview

When customers browse products in the Mercai, they can now watch product videos to get a better understanding of the items before purchasing.

---

## 📱 Customer User Flow

### 1. Browsing Products

**Scenario A: Product List with Video Indicator**
```
[Product List Screen]
┌─────────────────────────┐
│  🏺 Ceramic Vase        │
│  [Image]     [▶️ 0:45]  │  ← Video badge shows if product has video
│  $45.00 ⭐ 4.5 (23)     │
└─────────────────────────┘
```

**Future Enhancement:** Add video icon/badge in product cards to indicate which products have videos.

---

### 2. Viewing Product Details

**Step 1: Customer clicks on a product**
```
[Product List] → Tap Product → [Product Details Screen]
```

**Step 2: Product details load with video (if available)**
```
┌─────────────────────────────────────┐
│ ← Ceramic Handmade Vase        ❤️ 📤│
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │      Product Images         │    │
│  │      (Swipeable Gallery)    │    │
│  │                             │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │                             │    │
│  │    [▶️ PLAY BUTTON]         │    │  ← Large play button overlay
│  │                             │    │
│  │    Product Video            │    │
│  │    (0:45)                   │    │  ← Duration badge
│  │                             │    │
│  └─────────────────────────────┘    │
│                                     │
│  🏺 Category: Home Decor            │
│  Ceramic Handmade Vase              │
│  $45.00  ⭐ 4.5 (23 reviews)       │
│                                     │
│  [Add to Cart]  [Buy Now]          │
└─────────────────────────────────────┘
```

---

### 3. Playing the Video

**Step 3a: Customer sees the video section**
- Video displays below image gallery
- Large play button overlay is visible
- Duration badge shows video length (e.g., "0:45")

**Step 3b: Customer taps the play button**
```
Before Playing:                After Playing:
┌────────────────────┐        ┌────────────────────┐
│                    │        │  ┌──────────────┐  │
│       [▶️]         │        │  │  [⏸️]        │  │
│                    │   →    │  │              │  │
│    Video Thumbnail │        │  │ Video Playing│  │
│       0:45         │        │  │    0:23      │  │
└────────────────────┘        └────────────────────┘
```

**Video Controls:**
- **Play/Pause:** Tap center of video or play button
- **Seek:** Drag progress bar
- **Volume:** Use device volume buttons
- **Fullscreen:** Pinch to expand (future enhancement)

**Step 3c: Video playback**
- Video plays automatically
- Progress bar shows current position
- Customer can pause by tapping again
- Video loops when finished (optional)

---

### 4. Interaction Options

**While watching:**
- ✅ Play/Pause video
- ✅ Seek to different parts
- ✅ Adjust volume
- ✅ Continue browsing product details
- ✅ Add to cart (video continues playing)

**After watching:**
- ✅ Add product to cart
- ✅ Buy now
- ✅ Share product
- ✅ Write review
- ✅ View seller info

---

## 🎨 UI/UX Design

### Video Player States

#### 1. **Idle State** (Before Playing)
```
┌─────────────────────────────┐
│                             │
│        [▶️ PLAY]            │  ← Large, centered play button
│                             │
│         [0:45]              │  ← Duration badge (bottom-right)
└─────────────────────────────┘
```

**Design Elements:**
- Semi-transparent dark overlay on thumbnail
- 80px circular play button
- White play icon
- Duration badge with clock icon

#### 2. **Playing State**
```
┌─────────────────────────────┐
│  [⏸️]             🔊 ────●  │  ← Pause icon + volume
│                             │
│  ●───────────○──────────○  │  ← Progress bar
│  0:00        0:23      0:45│
└─────────────────────────────┘
```

**Design Elements:**
- Native video controls appear
- Progress bar with current time
- Pause icon instead of play
- Volume control

#### 3. **Completed State**
```
┌─────────────────────────────┐
│                             │
│     [🔄 REPLAY]             │  ← Replay button
│                             │
│         [0:45]              │
└─────────────────────────────┘
```

**Design Elements:**
- Replay button appears
- Video pauses at end
- Can tap to replay

---

## 🔧 Technical Implementation

### Component: `ProductVideoPlayer.jsx`

**Props:**
```javascript
{
  video: {
    video_url: string,        // Video file URL
    thumbnail_url: string,    // Auto-generated thumbnail
    duration_seconds: number, // Video duration in seconds
    resolution: string        // e.g., "1920x1080"
  }
}
```

**Features:**
- ✅ Auto-loads video metadata
- ✅ Play/pause toggle
- ✅ Custom play button overlay
- ✅ Duration display
- ✅ Loop playback
- ✅ Optimized for mobile

**State Management:**
```javascript
const [isPlaying, setIsPlaying] = useState(false);
const [isReady, setIsReady] = useState(false);
const videoRef = useRef(null);
```

---

## 📊 Video Display Logic

### When to Show Video Player

```javascript
{product.videos && product.videos.length > 0 && (
  <View style={styles.videoContainer}>
    <ProductVideoPlayer video={product.videos[0]} />
  </View>
)}
```

**Conditions:**
1. Product must have videos array
2. Videos array must have at least 1 video
3. Display first video ( MVP: 1 video per product)

**Position:**
- Below image gallery
- Above product info card
- Full width with margins

---

## 🎯 User Experience Goals

### 1. **Discoverability**
- ✅ Video section clearly visible
- ✅ Large, obvious play button
- ✅ Duration badge sets expectations

### 2. **Ease of Use**
- ✅ One-tap playback
- ✅ Intuitive controls
- ✅ No extra steps required

### 3. **Performance**
- ✅ Fast video loading
- ✅ Smooth playback
- ✅ Minimal data usage (optimized streaming)

### 4. **Accessibility**
- ✅ Large touch targets
- ✅ Clear visual feedback
- ✅ Works with screen readers (future)

---

## 📱 Responsive Design

### Phone (Portrait)
```
┌─────────────┐
│   Images    │
│  (swipe)    │
├─────────────┤
│   Video     │  ← Full width
│  (16:9)     │
├─────────────┤
│   Details   │
└─────────────┘
```

### Tablet (Landscape)
```
┌──────────────────────────────┐
│   Images    │    Video       │
│   (swipe)   │   (16:9)       │
├──────────────────────────────┤
│        Product Details       │
└──────────────────────────────┘
```

---

## 🧪 Testing Scenarios

### Functional Testing
- [ ] Video loads correctly
- [ ] Play button appears
- [ ] Video plays when tapped
- [ ] Pause works
- [ ] Seek/scrub works
- [ ] Volume control works
- [ ] Video loops (if enabled)
- [ ] Duration displays correctly

### UI Testing
- [ ] Video displays below images
- [ ] Proper spacing/margins
- [ ] Responsive on different screens
- [ ] Plays nicely with other content
- [ ] No layout shifts

### Performance Testing
- [ ] Fast video load time
- [ ] Smooth playback
- [ ] No app crashes
- [ ] Memory management OK
- [ ] Network usage reasonable

### User Testing
- [ ] Users notice video
- [ ] Users understand it's playable
- [ ] Users can play successfully
- [ ] Users find it helpful
- [ ] Users want more videos

---

## 🎬 Future Enhancements

### Phase 2
- [ ] Multiple videos per product (360° view)
- [ ] Video thumbnail selection
- [ ] Autoplay on scroll (muted)
- [ ] Video quality selector (360p, 720p, 1080p)
- [ ] Fullscreen mode

### Phase 3
- [ ] Video reviews from customers
- [ ] Live streaming product demos
- [ ] AR integration with video
- [ ] Video analytics (views, completion rate)
- [ ] Shoppable videos (tap to buy items in video)

---

## 📈 Success Metrics

Track these metrics:
- **Video Play Rate:** % of product views that include video playback
- **Completion Rate:** % of videos watched to completion
- **Engagement Time:** Time spent watching videos
- **Conversion Impact:** Purchase rate for products with videos vs. without
- **User Feedback:** Ratings/reviews mentioning videos

---

## 🐛 Troubleshooting

### Common Issues

**Video doesn't load:**
- Check internet connection
- Verify video URL is accessible
- Check file format compatibility

**Play button doesn't appear:**
- Verify product has video in database
- Check API response includes videos array
- Review console for errors

**Video won't play:**
- Check device compatibility
- Verify codec support (H.264 recommended)
- Test on physical device (not simulator)

**Playback is choppy:**
- Check network speed
- Reduce video quality/bitrates
- Implement adaptive streaming (future)

---

**Feature Status:** ✅ Complete  
**Ready for Customer Use:** ✅ Yes  
**Minimum iOS Version:** 12.0  
**Minimum Android Version:** 8.0  

---

*End of Customer Video Playback Documentation*
