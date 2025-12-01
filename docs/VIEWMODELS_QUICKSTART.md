# Quick Reference: ViewModels Pattern

## 🎯 TL;DR

**Problem:** Pages flicker/jump when auto-refreshing  
**Solution:** Use ViewModels + @ui.refreshable (no `.clear()`)  
**Result:** Zero flicker, smooth updates ✨

---

## 📋 Quick Start Template

```python
# 1. Create ViewModel (add to src/ui/viewmodels.py)
class MyViewModel:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.status = 'active'
    
    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.status})"

# 2. Use in page (src/ui/pages/my_page.py)
from src.ui.viewmodels import MyViewModel

@ui.page('/my-page')
async def my_page():
    # Initialize
    vms = {}
    
    # Render
    @ui.refreshable
    def render():
        for vm in vms.values():
            ui.label(vm.display_name)
    
    # Data loader
    async def load():
        items = await MyModel.all()
        for item in items:
            if item.id not in vms:
                vms[item.id] = MyViewModel(item.id, item.name)
            vms[item.id].status = item.status
        render.refresh()  # ← Magic happens here!
    
    # Setup
    await load()
    render()
    ui.timer(2.0, load)  # Auto-refresh
```

---

## ⚡ Common Patterns

### **Pattern 1: Simple List**
```python
vms = {}  # {id: ViewModel}

@ui.refreshable
def render():
    for vm in vms.values():
        with ui.card():
            ui.label(vm.name)

async def update():
    # Update ViewModels from DB
    render.refresh()
```

### **Pattern 2: Stats Dashboard**
```python
stats_vm = StatsViewModel()

@ui.refreshable
def render_stats():
    ui.label(f'Total: {stats_vm.total}')
    ui.label(f'Active: {stats_vm.active}')

async def update():
    stats_vm.total = await count_total()
    stats_vm.active = await count_active()
    render_stats.refresh()
```

### **Pattern 3: Nested Components**
```python
@ui.refreshable
def render_parent():
    for child_vm in parent_vm.children:
        render_child(child_vm)

@ui.refreshable  
def render_child(vm):
    ui.label(vm.name)

# Refresh both
render_parent.refresh()
render_child.refresh()
```

---

## ✅ Checklist for New Pages

- [ ] Create ViewModel in `src/ui/viewmodels.py`
- [ ] Add `@property` for formatted values
- [ ] Use `@ui.refreshable` decorator
- [ ] **NO** `.clear()` inside @ui.refreshable
- [ ] Store ViewModels in dict: `{id: ViewModel}`
- [ ] Create `async def load_data()` function
- [ ] Call `.refresh()` after updating ViewModels
- [ ] Add `ui.timer(interval, load_data)` if auto-refresh needed
- [ ] Test: scroll during refresh (should not jump)

---

## 🔧 Upgrading Existing Pages

**Before (Flickers):**
```python
@ui.refreshable
async def render():
    container.clear()  # ❌ BAD
    data = await fetch()
    with container:
        for item in data:
            ui.label(item.name)
```

**After (Smooth):**
```python
vms = {}

@ui.refreshable
def render():  # No .clear()!
    for vm in vms.values():
        ui.label(vm.name)

async def load():
    data = await fetch()
    for item in data:
        if item.id not in vms:
            vms[item.id] = ViewModel(...)
        vms[item.id].name = item.name
    render.refresh()
```

---

## 📊 Refresh Intervals

| Page Type | Interval | Example |
|-----------|----------|---------|
| Critical monitoring | 1-2s | Batch progress |
| Active updates | 3-5s | Chat messages |
| Awareness | 10-30s | Navbar stats |
| Background sync | 60s+ | User sessions |

**Rule of thumb:** If user is actively watching it, use 2-5s. Otherwise 30s+.

---

## 🐛 Common Mistakes

### ❌ Mistake 1: Forgetting .refresh()
```python
async def update():
    vm.count = new_count
    # Forgot render.refresh() - UI won't update!
```

### ❌ Mistake 2: Using .clear() in @ui.refreshable
```python
@ui.refreshable
def render():
    container.clear()  # ← Causes flicker!
```

### ❌ Mistake 3: Not tracking deletions
```python
async def load():
    items = await Item.all()
    for item in items:
        vms[item.id] = ...
    # ← Forgot to remove deleted items from vms dict!
```

**Fix:**
```python
async def load():
    items = await Item.all()
    db_ids = {item.id for item in items}
    
    # Update/add
    for item in items:
        vms[item.id] = ...
    
    # Remove deleted
    for vm_id in list(vms.keys()):
        if vm_id not in db_ids:
            del vms[vm_id]
```

---

## 💡 Pro Tips

1. **Cache computed properties:**
   ```python
   @property
   def expensive_calc(self):
       if not hasattr(self, '_cached'):
           self._cached = heavy_calculation()
       return self._cached
   ```

2. **Batch database queries:**
   ```python
   # ❌ N+1 queries
   for item in items:
       count = await Message.filter(item_id=item.id).count()
   
   # ✅ Single query
   items = await Item.all().annotate(
       msg_count=Count('messages')
   )
   ```

3. **Use ViewModels everywhere:**
   ```python
   # Create once, use in multiple pages:
   vm = ExperimentViewModel(...)
   
   # Batch page:
   render_batch_card(vm)
   
   # Experiments page:
   render_experiment_row(vm)
   
   # Both auto-sync when you update vm.status!
   ```

---

## 📁 File Locations

- **ViewModels:** `src/ui/viewmodels.py`
- **Example:** `src/ui/pages/batch_progress.py`
- **Tests:** `tests/test_viewmodels.py`
- **Full Docs:** `docs/VIEWMODELS_ARCHITECTURE.md`

---

## 🆘 Need Help?

1. Check full architecture doc: `docs/VIEWMODELS_ARCHITECTURE.md`
2. Look at working example: `src/ui/pages/batch_progress.py`
3. Run tests: `cd tests && python3 test_viewmodels.py`

**Remember:** ViewModels = Data container, @ui.refreshable = Smart renderer, No .clear() = No flicker!
