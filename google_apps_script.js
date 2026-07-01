// ==============================================================================
// 🚀 GOOGLE APPS SCRIPT: GÓC TỐI PHÁP LUẬT AUTOMATION MENU
// ==============================================================================
// HƯỚNG DẪN CÀI ĐẶT:
// 1. Mở file Google Sheet của anh.
// 2. Vào phần Extensions (Tiện ích mở rộng) -> chọn Apps Script.
// 3. Xóa hết code mặc định và dán toàn bộ đoạn code dưới đây vào.
// 4. Bấm Save (Ctrl+S).
// 5. Reload lại trang Google Sheet. Anh sẽ thấy menu "🚀 Góc Tối Pháp Luật Orchestrator" xuất hiện.
// ==============================================================================

const GH_OWNER = "lchau4501-collab";
const GH_TOKEN = "YOUR_GITHUB_TOKEN_HERE"; // GitHub Token của anh
// Cấu hình URL Cloudflare Worker (thay thế sau khi anh xác định subdomain)
const CF_WORKER_URL = "https://goc-toi-phap-luat-orchestrator.lchau4501.workers.dev";
const GDRIVE_PARENT_FOLDER_ID = "1BABIF2g-U6RqAgNyjs7hOACOiPmFvYPC"; // ID thư mục Drive cha của anh

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 Góc Tối Pháp Luật Orchestrator')
    .addItem('0. Trigger All (Active Row)', 'triggerAll')
    .addSeparator()
    .addItem('1. Run Step 1 (New Idea)', 'runStep1')
    .addSeparator()
    .addItem('2a. Run Step 2 - Selected Row (Scripting)', 'runStep2')
    .addItem('2b. Run Step 2 - All Pending Rows (Scripting)', 'runStep2AllPending')
    .addSeparator()
    .addItem('3a. Run Step 3 - Selected Row (Prompts)', 'runStep3')
    .addItem('3b. Run Step 3 - All Script Rows (Prompts)', 'runStep3AllScript')
    .addSeparator()
    .addItem('4. Check Duplication (Proposal C1)', 'checkDuplication')
    .addItem('5. Move Chosen Rows to goctoiphapluat', 'moveChosenToGoctoiphapluat')
    .addToUi();
}

/**
 * 1. Kích hoạt Step 1 (Gọi Cloudflare Worker tạo ý tưởng mới)
 */
function runStep1() {
  const response = UrlFetchApp.fetch(CF_WORKER_URL, {
    method: 'post',
    payload: JSON.stringify({ action: 'ideate' }),
    contentType: 'application/json',
    muteHttpExceptions: true
  });
  
  if (response.getResponseCode() === 200 || response.getResponseCode() === 202) {
    SpreadsheetApp.getUi().alert('Success: Step 1 (Ideation) triggered on Cloudflare Worker!');
  } else {
    SpreadsheetApp.getUi().alert('Error: Failed to trigger Step 1. Response: ' + response.getContentText());
  }
}

/**
 * Hàm phụ lấy thông tin dòng đang được chọn (Active Row)
 */
function getSelectedRowData() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const range = sheet.getActiveRange();
  const rowIdx = range.getRow();
  
  if (rowIdx === 1) {
    SpreadsheetApp.getUi().alert('Vui lòng chọn một dòng tập phim cụ thể (Không chọn dòng tiêu đề số 1).');
    return null;
  }
  
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const rowValues = sheet.getRange(rowIdx, 1, 1, sheet.getLastColumn()).getValues()[0];
  
  const data = {};
  headers.forEach((header, index) => {
    data[header.trim()] = rowValues[index];
  });
  
  if (!data['ID']) {
    SpreadsheetApp.getUi().alert('Lỗi: Dòng được chọn không chứa thông tin ID hợp lệ.');
    return null;
  }
  
  return {
    rowIdx: rowIdx,
    id: data['ID'],
    figure: data['Historical Figure'],
    title: data['Video Title']
  };
}

/**
 * 2. Kích hoạt Step 2 (Gửi Dispatch gọi GHA viết kịch bản)
 */
function runStep2() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const rowData = getSelectedRowData();
  if (!rowData) return;
  
  // Kiểm tra và tự động tạo thư mục Google Drive nếu chưa có
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const folderColIdx = headers.indexOf('GDrive Folder Link') + 1;
  
  // Đọc lại giá trị hiện tại ở dòng đang chọn
  let folderUrl = "";
  if (folderColIdx > 0) {
    folderUrl = sheet.getRange(rowData.rowIdx, folderColIdx).getValue();
  }
  
  if (!folderUrl && folderColIdx > 0) {
    try {
      const parentFolder = DriveApp.getFolderById(GDRIVE_PARENT_FOLDER_ID);
      const newFolder = parentFolder.createFolder(rowData.title || rowData.figure);
      folderUrl = newFolder.getUrl();
      sheet.getRange(rowData.rowIdx, folderColIdx).setValue(folderUrl);
      SpreadsheetApp.getActiveSpreadsheet().toast("Đã tự động tạo thư mục GDrive: " + folderUrl, "GDrive Info");
    } catch (e) {
      SpreadsheetApp.getUi().alert("Lỗi khi tự động tạo thư mục GDrive: " + e.message);
      return;
    }
  }
  
  const prompt = `Viết kịch bản chi tiết về vụ án ${rowData.figure}: ${rowData.title} bằng tiếng Việt, theo phong cách Góc Tối Pháp Luật.`;
  const url = `https://api.github.com/repos/${GH_OWNER}/goctoiphapluat-step2-scripting/dispatches`;
  
  const payload = {
    event_type: "run-scripting",
    client_payload: {
      id: rowData.id,
      prompt: prompt
    }
  };
  
  const options = {
    method: 'post',
    headers: {
      'Authorization': 'token ' + GH_TOKEN,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'GoogleAppsScript'
    },
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() === 204) {
    SpreadsheetApp.getUi().alert('Success: Step 2 (Scripting) workflow triggered on GitHub!');
  } else {
    SpreadsheetApp.getUi().alert('Error: Failed to trigger Step 2. Response: ' + response.getContentText());
  }
}

/**
 * 3. Kích hoạt Step 3 (Gửi Dispatch gọi GHA tạo Prompts ảnh)
 */
function runStep3() {
  const rowData = getSelectedRowData();
  if (!rowData) return;
  
  const url = `https://api.github.com/repos/${GH_OWNER}/goctoiphapluat-step3-prompts/dispatches`;
  
  const payload = {
    event_type: "run-prompts",
    client_payload: {
      id: rowData.id
    }
  };
  
  const options = {
    method: 'post',
    headers: {
      'Authorization': 'token ' + GH_TOKEN,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'GoogleAppsScript'
    },
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() === 204) {
    SpreadsheetApp.getUi().alert('Success: Step 3 (Prompts) workflow triggered on GitHub!');
  } else {
    SpreadsheetApp.getUi().alert('Error: Failed to trigger Step 3. Response: ' + response.getContentText());
  }
}

/**
 * 0. Kích hoạt toàn bộ luồng (Kích hoạt Step 2 và tự động nối tiếp Step 3)
 */
function triggerAll() {
  const rowData = getSelectedRowData();
  if (!rowData) return;
  
  // Chạy Step 2, sau khi viết xong kịch bản GHA của Step 2 sẽ tự động gọi tiếp sang Step 3.
  runStep2();
}

/**
 * 2b. Kích hoạt viết kịch bản cho toàn bộ các dòng ở trạng thái pending
 */
function runStep2AllPending() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const historySheet = ss.getSheetByName("goctoiphapluat");
  if (!historySheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'goctoiphapluat'.");
    return;
  }
  
  const lastRow = historySheet.getLastRow();
  let pendingCount = 0;
  if (lastRow >= 2) {
    const values = historySheet.getRange(2, 4, lastRow - 1, 1).getValues();
    for (let i = 0; i < values.length; i++) {
      if (values[i][0].toString().trim().toLowerCase() === "pending") {
        pendingCount++;
      }
    }
  }
  
  if (pendingCount === 0) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tập phim nào có trạng thái 'pending' để chạy viết kịch bản.");
    return;
  }
  
  const uiResponse = SpreadsheetApp.getUi().alert(
    "Xác nhận",
    `Tìm thấy ${pendingCount} tập phim có trạng thái 'pending'. Bạn có chắc chắn muốn kích hoạt viết kịch bản hàng loạt?`,
    SpreadsheetApp.getUi().ButtonSet.YES_NO
  );
  
  if (uiResponse !== SpreadsheetApp.getUi().Button.YES) {
    return;
  }
  
  const url = `https://api.github.com/repos/${GH_OWNER}/goctoiphapluat-step2-scripting/dispatches`;
  const payload = {
    event_type: "run-scripting"
  };
  
  const options = {
    method: 'post',
    headers: {
      'Authorization': 'token ' + GH_TOKEN,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'GoogleAppsScript'
    },
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() === 204) {
    SpreadsheetApp.getUi().alert('Success: Step 2 workflow triggered for ALL pending rows on GitHub!');
  } else {
    SpreadsheetApp.getUi().alert('Error: Failed to trigger Step 2. Response: ' + response.getContentText());
  }
}

/**
 * 3b. Kích hoạt tạo Image Prompts cho toàn bộ các dòng ở trạng thái script
 */
function runStep3AllScript() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const historySheet = ss.getSheetByName("goctoiphapluat");
  if (!historySheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'goctoiphapluat'.");
    return;
  }
  
  const lastRow = historySheet.getLastRow();
  let hasPending = false;
  let scriptCount = 0;
  
  if (lastRow >= 2) {
    const values = historySheet.getRange(2, 4, lastRow - 1, 1).getValues();
    for (let i = 0; i < values.length; i++) {
      const val = values[i][0].toString().trim().toLowerCase();
      if (val === "pending") {
        hasPending = true;
      } else if (val === "script") {
        scriptCount++;
      }
    }
  }
  
  if (hasPending) {
    SpreadsheetApp.getUi().alert("Không thể chạy Step 3 vì vẫn còn các dòng có trạng thái 'pending' chưa hoàn thành Step 2.");
    return;
  }
  
  if (scriptCount === 0) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tập phim nào có trạng thái 'script' để chạy tạo Image Prompts.");
    return;
  }
  
  const uiResponse = SpreadsheetApp.getUi().alert(
    "Xác nhận",
    `Tìm thấy ${scriptCount} tập phim có trạng thái 'script'. Bạn có chắc chắn muốn kích hoạt tạo Image Prompts hàng loạt?`,
    SpreadsheetApp.getUi().ButtonSet.YES_NO
  );
  
  if (uiResponse !== SpreadsheetApp.getUi().Button.YES) {
    return;
  }
  
  const url = `https://api.github.com/repos/${GH_OWNER}/goctoiphapluat-step3-prompts/dispatches`;
  const payload = {
    event_type: "run-prompts"
  };
  
  const options = {
    method: 'post',
    headers: {
      'Authorization': 'token ' + GH_TOKEN,
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'GoogleAppsScript'
    },
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  
  const response = UrlFetchApp.fetch(url, options);
  
  if (response.getResponseCode() === 204) {
    SpreadsheetApp.getUi().alert('Success: Step 3 workflow triggered for ALL script rows on GitHub!');
  } else {
    SpreadsheetApp.getUi().alert('Error: Failed to trigger Step 3. Response: ' + response.getContentText());
  }
}

/**
 * Helper: Phát sinh UUID trong Google Apps Script
 */
function generateUUID() {
  return Utilities.getUuid();
}

/**
 * Helper: Lấy ngày giờ định dạng GMT+7 Việt Nam
 */
function getGMT7DateTimeString() {
  return Utilities.formatDate(new Date(), "GMT+7", "yyyy-MM-dd HH:mm:ss");
}

/**
 * Cơ chế kiểm tra trùng lặp cho Proposal nằm ở C1 của tab sheet "ideation"
 * So sánh với cột B (từ dòng 2 trở đi) của tab sheet "goctoiphapluat"
 * Trả kết quả "⛔ Duplicated" hoặc "✅Passed" vào ô E1
 */
function checkDuplication() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ideationSheet = ss.getSheetByName("ideation");
  if (!ideationSheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'ideation'.");
    return;
  }
  
  const proposalVal = ideationSheet.getRange("C1").getValue().toString().trim();
  if (!proposalVal) {
    ideationSheet.getRange("E1").setValue("");
    SpreadsheetApp.getUi().alert("Ô C1 (Proposal) đang trống, vui lòng nhập giá trị trước khi check.");
    return;
  }
  
  const masterSheet = ss.getSheetByName("goctoiphapluat");
  if (!masterSheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'goctoiphapluat'.");
    return;
  }
  
  const lastRow = masterSheet.getLastRow();
  if (lastRow < 2) {
    ideationSheet.getRange("E1").setValue("✅Passed");
    SpreadsheetApp.getActiveSpreadsheet().toast("Đã kiểm tra trùng lặp cho: " + proposalVal, "Check Duplication Done");
    return;
  }
  
  const values = masterSheet.getRange(2, 2, lastRow - 1, 1).getValues();
  const proposalLower = proposalVal.toLowerCase();
  
  let isDuplicated = false;
  for (let i = 0; i < values.length; i++) {
    const historicalFigure = values[i][0].toString().trim().toLowerCase();
    if (historicalFigure === proposalLower) {
      isDuplicated = true;
      break;
    }
  }
  
  if (isDuplicated) {
    ideationSheet.getRange("E1").setValue("⛔ Duplicated");
  } else {
    ideationSheet.getRange("E1").setValue("✅Passed");
  }
  
  SpreadsheetApp.getActiveSpreadsheet().toast("Đã kiểm tra trùng lặp cho: " + proposalVal, "Check Duplication Done");
}

/**
 * Tìm dòng trên cùng trống hoàn toàn trong sheet
 */
function getFirstEmptyRowInGoctoiphapluat(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return 2;
  
  const maxCols = sheet.getLastColumn() || 11;
  const values = sheet.getRange(2, 1, lastRow - 1, maxCols).getValues();
  
  for (let i = 0; i < values.length; i++) {
    const row = values[i];
    let isEmpty = true;
    for (let j = 0; j < row.length; j++) {
      if (row[j] !== null && row[j] !== "") {
        isEmpty = false;
        break;
      }
    }
    if (isEmpty) {
      return i + 2;
    }
  }
  return lastRow + 1;
}

/**
 * Chuyển các dòng có status "chosen" từ tab "ideation" sang tab "goctoiphapluat"
 */
function moveChosenToGoctoiphapluat() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ideationSheet = ss.getSheetByName("ideation");
  if (!ideationSheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'ideation'.");
    return;
  }
  
  const masterSheet = ss.getSheetByName("goctoiphapluat");
  if (!masterSheet) {
    SpreadsheetApp.getUi().alert("Không tìm thấy tab sheet 'goctoiphapluat'.");
    return;
  }
  
  const lastRowIdeation = ideationSheet.getLastRow();
  if (lastRowIdeation < 3) {
    SpreadsheetApp.getUi().alert("Tab 'ideation' không có dữ liệu để chuyển.");
    return;
  }
  
  const ideationValues = ideationSheet.getRange(3, 1, lastRowIdeation - 2, 5).getValues();
  let countMoved = 0;
  
  for (let i = 0; i < ideationValues.length; i++) {
    const row = ideationValues[i];
    const id = row[0];
    const figure = row[1];
    const title = row[2];
    const status = row[3].toString().trim().toLowerCase();
    
    if (status === "chosen") {
      const destRowIdx = getFirstEmptyRowInGoctoiphapluat(masterSheet);
      const nowStr = getGMT7DateTimeString();
      
      const destValues = [
        id || generateUUID(),
        figure,
        title,
        "pending",
        "", "", "", "", "",
        nowStr,
        ""
      ];
      
      masterSheet.getRange(destRowIdx, 1, 1, 11).setValues([destValues]);
      ideationSheet.getRange(i + 3, 4).setValue("moved");
      countMoved++;
    }
  }
  
  if (countMoved > 0) {
    SpreadsheetApp.getUi().alert(`Đã chuyển thành công ${countMoved} dòng có trạng thái 'chosen' sang tab 'goctoiphapluat' với trạng thái 'pending'.`);
  } else {
    SpreadsheetApp.getUi().alert("Không tìm thấy dòng nào có trạng thái 'chosen' để chuyển.");
  }
}
