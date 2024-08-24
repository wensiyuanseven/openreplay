# 这个代码定义了一组用于可用性测试 (Usability Test, UT) 的数据模型和相关验证逻辑，基于 `Pydantic` 库进行数据验证和处理。
# 每个类对应于不同的使用场景，如创建、更新、删除和搜索可用性测试及其相关任务、会话、响应等。
from typing import Optional, List
from pydantic import Field
from datetime import datetime
from enum import Enum
from schemas import BaseModel

from pydantic.v1 import validator


class StatusEnum(str, Enum):
    preview = "preview"
    in_progress = "in-progress"
    paused = "paused"
    closed = "closed"


class UTTestTask(BaseModel):
    task_id: Optional[int] = Field(None, description="The unique identifier of the task")
    test_id: Optional[int] = Field(None, description="The unique identifier of the usability test")
    title: str = Field(..., description="The title of the task")
    description: Optional[str] = Field(None, description="A detailed description of the task")
    allow_typing: Optional[bool] = Field(False, description="Indicates if the user is allowed to type")


class UTTestBase(BaseModel):
    title: str = Field(..., description="The title of the usability test")
    project_id: Optional[int] = Field(None, description="The ID of the associated project")
    created_by: Optional[int] = Field(None, description="The ID of the user who created the test")
    starting_path: Optional[str] = Field(None, description="The starting path for the usability test")
    status: Optional[StatusEnum] = Field(StatusEnum.in_progress, description="The current status of the usability test")
    require_mic: bool = Field(False, description="Indicates if a microphone is required")
    require_camera: bool = Field(False, description="Indicates if a camera is required")
    description: Optional[str] = Field(None, description="A detailed description of the usability test")
    guidelines: Optional[str] = Field(None, description="Guidelines for the usability test")
    conclusion_message: Optional[str] = Field(None, description="Conclusion message for the test participants")
    visibility: bool = Field(False, description="Flag to indicate if the test is visible to the public")
    tasks: Optional[List[UTTestTask]] = Field(None, description="List of tasks for the usability test")


class UTTestCreate(UTTestBase):
    pass


class UTTestStatusUpdate(BaseModel):
    status: StatusEnum = Field(..., description="The updated status of the usability test")


class UTTestRead(UTTestBase):
    test_id: int = Field(..., description="The unique identifier of the usability test")
    created_by: Optional[int] = Field(None, description="The ID of the user who created the test")
    updated_by: Optional[int] = Field(None, description="The ID of the user who last updated the test")
    created_at: datetime = Field(..., description="The timestamp when the test was created")
    updated_at: datetime = Field(..., description="The timestamp when the test was last updated")
    deleted_at: Optional[datetime] = Field(None, description="The timestamp when the test was deleted, if applicable")


class UTTestUpdate(BaseModel):
    # Optional fields for updating the usability test
    title: Optional[str] = Field(None, description="The updated title of the usability test")
    status: Optional[StatusEnum] = Field(None, description="The updated status of the usability test")
    description: Optional[str] = Field(None, description="The updated description of the usability test")
    starting_path: Optional[str] = Field(None, description="The updated starting path for the usability test")
    require_mic: Optional[bool] = Field(None, description="Indicates if a microphone is required")
    require_camera: Optional[bool] = Field(None, description="Indicates if a camera is required")
    guidelines: Optional[str] = Field(None, description="Updated guidelines for the usability test")
    conclusion_message: Optional[str] = Field(None, description="Updated conclusion message for the test participants")
    visibility: Optional[bool] = Field(None, description="Flag to indicate if the test is visible to the public")
    tasks: Optional[List[UTTestTask]] = Field([], description="List of tasks for the usability test")


class UTTestDelete(BaseModel):
    # You would usually not need a model for deletion, but let's assume you need to confirm the deletion timestamp
    deleted_at: datetime = Field(..., description="The timestamp when the test is marked as deleted")


class UTTestSearch(BaseModel):
    query: Optional[str] = Field(None, description="Search query for the UT tests")
    page: Optional[int] = Field(1, ge=1, description="Page number of the results")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of results per page")
    sort_by: Optional[str] = Field(description="Field to sort by", default="created_at")
    sort_order: Optional[str] = Field("asc", description="Sort order: 'asc' or 'desc'")
    is_active: Optional[bool] = Field(True, description="Flag to indicate if the test is active")
    user_id: Optional[int] = Field(None, description="The ID of the user who created the test")

    @validator("sort_order")
    def sort_order_must_be_valid(cls, v):
        if v not in ["asc", "desc"]:
            raise ValueError('Sort order must be either "asc" or "desc"')
        return v


class UTTestResponsesSearch(BaseModel):
    query: Optional[str] = Field(None, description="Search query for the UT responses")
    page: Optional[int] = Field(1, ge=1, description="Page number of the results")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of results per page")


class UTTestSignal(BaseModel):
    signal_id: int = Field(..., description="The unique identifier of the response")
    test_id: int = Field(..., description="The unique identifier of the usability test")
    session_id: int = Field(..., description="The unique identifier of the session")
    type: str = Field(..., description="The type of the signal")
    type_id: int = Field(..., description="The unique identifier of the type")
    status: str = Field(..., description="The status of the signal")
    comment: Optional[str] = Field(None, description="The comment for the signal")
    timestamp: datetime = Field(..., description="The timestamp when the signal was created")


class UTTestResponse(BaseModel):
    test_id: int = Field(..., description="The unique identifier of the usability test")
    response_id: str = Field(..., description="The type of the signal")
    status: str = Field(..., description="The status of the signal")
    comment: Optional[str] = Field(None, description="The comment for the signal")
    timestamp: datetime = Field(..., description="The timestamp when the signal was created")


class UTTestSession(BaseModel):
    test_id: int = Field(..., description="The unique identifier of the usability test")
    session_id: int = Field(..., description="The unique identifier of the session")
    status: str = Field(..., description="The status of the signal")
    timestamp: datetime = Field(..., description="The timestamp when the signal was created")


class UTTestSessionsSearch(BaseModel):
    page: Optional[int] = Field(1, ge=1, description="Page number of the results")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Number of results per page")
    status: Optional[str] = Field(None, description="The status of the session")


class SearchResult(BaseModel):
    results: List[UTTestRead]
    total: int
    page: int
    limit: int


# 这个代码定义了一组用于可用性测试 (Usability Test, UT) 的数据模型和相关验证逻辑，基于 `Pydantic` 库进行数据验证和处理。每个类对应于不同的使用场景，如创建、更新、删除和搜索可用性测试及其相关任务、会话、响应等。

# ### 主要类和字段解释

# 1. **`StatusEnum` (枚举类)**：
#    - 定义了可用性测试的状态，包括 `preview`、`in-progress`、`paused` 和 `closed`。
#    - **用途**：用于表示可用性测试的当前状态。

# 2. **`UTTestTask` (任务模型)**：
#    - 定义了与可用性测试关联的单个任务，包括任务 ID、测试 ID、标题、描述以及用户是否可以输入的标志。
#    - **字段**：
#      - `task_id`：任务的唯一标识符。
#      - `title`：任务的标题。
#      - `allow_typing`：是否允许用户输入。

# 3. **`UTTestBase` (可用性测试基本模型)**：
#    - 定义了可用性测试的基本信息，包含测试标题、项目 ID、创建者 ID、状态、是否需要麦克风和摄像头、任务列表等。
#    - **字段**：
#      - `title`：可用性测试的标题。
#      - `require_mic` 和 `require_camera`：是否需要麦克风或摄像头。
#      - `tasks`：与测试关联的任务列表。

# 4. **`UTTestCreate` (创建模型)**：
#    - 用于创建可用性测试，继承自 `UTTestBase`。

# 5. **`UTTestStatusUpdate` (状态更新模型)**：
#    - 用于更新可用性测试的状态。
#    - **字段**：
#      - `status`：更新后的可用性测试状态。

# 6. **`UTTestRead` (读取模型)**：
#    - 包含从数据库中读取的可用性测试的详细信息，包含测试 ID、创建时间、更新时间等。
#    - **字段**：
#      - `test_id`：测试的唯一标识符。
#      - `created_at` 和 `updated_at`：测试的创建和更新时间。

# 7. **`UTTestUpdate` (更新模型)**：
#    - 用于部分更新可用性测试的字段，包括状态、标题、描述等。
#    - **字段**：
#      - 可选字段如 `title`、`status`、`description` 等，可以更新测试的各个属性。

# 8. **`UTTestDelete` (删除模型)**：
#    - 用于表示测试删除操作，包括删除时间。
#    - **字段**：
#      - `deleted_at`：测试被标记为删除的时间。

# 9. **`UTTestSearch` (搜索模型)**：
#    - 用于搜索可用性测试，支持分页、排序、关键字查询等。
#    - **字段**：
#      - `query`：搜索关键字。
#      - `page` 和 `limit`：用于分页的参数。
#      - `sort_by` 和 `sort_order`：排序字段和顺序。

# 10. **`UTTestResponsesSearch` (响应搜索模型)**：
#     - 类似于 `UTTestSearch`，用于搜索响应，支持分页和关键字查询。

# 11. **`UTTestSignal` (信号模型)**：
#     - 定义与可用性测试相关的信号信息，如信号类型、状态、时间戳等。
#     - **字段**：
#       - `signal_id` 和 `test_id`：信号和测试的唯一标识符。
#       - `status`：信号的状态。

# 12. **`UTTestResponse` (响应模型)**：
#     - 定义了可用性测试的响应，包括响应 ID、状态、注释等。

# 13. **`UTTestSession` (会话模型)**：
#     - 表示可用性测试的会话信息。

# 14. **`UTTestSessionsSearch` (会话搜索模型)**：
#     - 用于搜索与可用性测试相关的会话，支持分页和状态过滤。

# 15. **`SearchResult` (搜索结果模型)**：
#     - 包含了搜索的结果列表和分页信息。

# ### 总结

# 这些类通过 `Pydantic` 实现了数据验证和序列化，主要用于可用性测试模块的各类操作，包括创建、更新、删除、搜索、任务管理、信号记录等。